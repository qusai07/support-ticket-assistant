"""Glue between the graph and the database: create, process, persist, review."""
import time
import uuid

from sqlmodel import Session, select

from app.db.session import engine
from app.llm.client import track_usage
from app.models import db
from app.models.enums import ReviewDecision, TicketStatus
from app.models.schemas import ReviewIn, TicketIn
from app.pipeline.graph import GRAPH


def create_ticket(t: TicketIn, ticket_id: str | None = None, enqueue: bool = True) -> str:
    """Insert the ticket and its processing job in ONE transaction (outbox pattern):
    a ticket can never exist without a job to process it."""
    ticket_id = ticket_id or f"TCK-{uuid.uuid4().hex[:8].upper()}"
    with Session(engine) as s:
        s.add(db.Ticket(id=ticket_id, subject=t.subject, body=t.body, customer_email=t.customer_email,
                        channel=t.channel.value, created_at=db.as_utc(t.created_at)))
        if enqueue:
            s.flush()
            s.add(db.Job(ticket_id=ticket_id))
        s.commit()
    return ticket_id


def is_transient(e: BaseException) -> bool:
    """Errors worth retrying: the model server was slow, busy or briefly unreachable."""
    import httpx
    seen: BaseException | None = e
    while seen is not None:  # look through wrapped causes too
        if isinstance(seen, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError, TimeoutError, ConnectionError)):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def process_ticket(ticket_id: str, t: TicketIn, retry_transient: bool = False) -> dict:
    """Run the graph and persist everything. Failures go to a human, never to the customer.

    retry_transient=True (worker mode): a TRANSIENT error (LLM timeout, connection refused)
    is re-raised instead, so the job queue retries it later; after the last attempt the
    queue sends the ticket to a human. Permanent errors go to a human immediately."""
    t0 = time.perf_counter()
    with track_usage() as calls:
        try:
            state = GRAPH.invoke({"ticket_id": ticket_id, "ticket": t})
        except Exception as e:
            if retry_transient and is_transient(e):
                raise
            state = {"status": TicketStatus.in_review, "status_reasons": [f"pipeline_error: {type(e).__name__}: {e}"]}
    total_ms = int((time.perf_counter() - t0) * 1000)

    with Session(engine) as s:
        if "triage" in state:
            s.add(db.TriageRecord(ticket_id=ticket_id, result=state["triage"].model_dump(mode="json")))
        agent = state.get("agent")
        s.add(db.PipelineRun(
            ticket_id=ticket_id,
            retrieved=[d.model_dump() for d in state.get("docs", [])],
            routing=state["routing"].model_dump() if "routing" in state else {},
            agent_output=agent.output.model_dump(mode="json") if agent else None,
            status_reasons=state.get("status_reasons", []),
            guardrail_flags=agent.guardrail_flags if agent else [],
            raw_confidence=agent.raw_confidence if agent else None,
            timings_ms=state.get("timings_ms", {}),
            final_status=state["status"], total_latency_ms=total_ms,
        ))
        if agent:
            for i, c in enumerate(agent.trace):
                s.add(db.ToolCallRecord(ticket_id=ticket_id, seq=i, step=c.step, tool=c.tool, args=c.args,
                                        result=c.result, error=c.error, latency_ms=c.latency_ms))
        for c in calls:
            s.add(db.LLMCall(ticket_id=ticket_id, purpose=c.purpose, model=c.model, input_tokens=c.input_tokens,
                             output_tokens=c.output_tokens, latency_ms=c.latency_ms))
        if esc := state.get("escalation"):
            s.add(db.Escalation(ticket_id=ticket_id, **esc))
        ticket = s.get(db.Ticket, ticket_id)
        ticket.status, ticket.updated_at = state["status"], db._now()
        # Denormalized onto the ticket so queue filters and permission scoping are simple indexed queries.
        ticket.team = state["routing"].team if "routing" in state else (ticket.team or "Customer Care")
        if tri := state.get("triage"):
            ticket.priority, ticket.language = tri.priority.value, tri.language
        s.commit()
    return state


def submit(t: TicketIn) -> tuple[str, dict]:
    """Synchronous path (scripts/tests): create without a job and process inline."""
    tid = create_ticket(t, enqueue=False)
    return tid, process_ticket(tid, t)


def review(ticket_id: str, r: ReviewIn, user: db.User | None = None) -> db.Review:
    with Session(engine) as s:
        ticket = s.get(db.Ticket, ticket_id)
        if ticket is None:
            raise KeyError(ticket_id)
        run = s.exec(select(db.PipelineRun).where(db.PipelineRun.ticket_id == ticket_id)
                     .order_by(db.PipelineRun.id.desc())).first()
        original = (run.agent_output or {}).get("draft_reply", "") if run else ""

        final = {ReviewDecision.approve: original, ReviewDecision.edit: r.edited_reply}.get(r.decision)
        ticket.status = {
            ReviewDecision.approve: TicketStatus.approved,
            ReviewDecision.edit: TicketStatus.approved,
            ReviewDecision.reject: TicketStatus.rejected,
            ReviewDecision.escalate: TicketStatus.escalated,
        }[r.decision]
        ticket.updated_at = db._now()
        if r.decision == ReviewDecision.escalate:
            s.add(db.Escalation(ticket_id=ticket_id, reason="reviewer_escalated",
                                summary=r.comment or "Escalated by reviewer.", source="reviewer"))
        rec = db.Review(ticket_id=ticket_id, decision=r.decision.value, original_reply=original,
                        final_reply=final, reviewer=user.full_name if user else r.reviewer,
                        reviewer_id=user.id if user else None, comment=r.comment)
        if user:
            s.add(db.AuditLog(user_id=user.id, action="ticket.review", target_type="ticket", target_id=ticket_id,
                              detail={"decision": r.decision.value}))
        s.add(rec)
        s.commit()
        s.refresh(rec)
        return rec


def ticket_detail(ticket_id: str) -> dict | None:
    with Session(engine) as s:
        t = s.get(db.Ticket, ticket_id)
        if t is None:
            return None

        def rows(model):
            return [r.model_dump(mode="json") for r in
                    s.exec(select(model).where(model.ticket_id == ticket_id).order_by(model.id)).all()]

        triage = rows(db.TriageRecord)
        runs = rows(db.PipelineRun)
        assignee = s.get(db.User, t.assignee_id) if t.assignee_id else None
        return {
            "ticket": t.model_dump(mode="json"),
            "assignee": {"id": assignee.id, "full_name": assignee.full_name} if assignee else None,
            "triage": triage[-1]["result"] if triage else None,
            "run": runs[-1] if runs else None,
            "tool_calls": rows(db.ToolCallRecord),
            "llm_calls": rows(db.LLMCall),
            "escalations": rows(db.Escalation),
            "reviews": rows(db.Review),
        }
