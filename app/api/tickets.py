"""Ticket endpoints. Every route is authenticated; queries are scoped by team.

Note: a forbidden ticket returns 404, not 403. Answering "exists but not yours"
would leak which ticket IDs exist.
"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.deps import audit, can_see_ticket, require
from app.auth.permissions import Permission, has_permission, team_names
from app.db.session import get_session
from app.jobs.queue import queue_depth
from app.models import db
from app.models.enums import TicketStatus
from app.models.schemas import ReviewIn, TicketIn
from app.pipeline import service
from app.sla import RESOLVING_DECISIONS, sla_for

router = APIRouter(prefix="/tickets", tags=["tickets"])
P = Permission


def _scoped(q, user: db.User):
    if has_permission(user.role, P.TICKETS_VIEW_ALL):
        return q
    return q.where((db.Ticket.team == user.team) | (db.Ticket.assignee_id == user.id))


def _get_visible(session: Session, user: db.User, ticket_id: str) -> db.Ticket:
    t = session.get(db.Ticket, ticket_id)
    if t is None or not can_see_ticket(user, t):
        raise HTTPException(404, "ticket not found")
    return t


@router.post("", status_code=202)
def submit_ticket(t: TicketIn, request: Request, user: db.User = Depends(require(P.TICKETS_CREATE)),
                  session: Session = Depends(get_session)):
    """Accept a ticket; a worker processes it (python -m app.worker)."""
    tid = service.create_ticket(t)
    audit(session, user, "ticket.create", "ticket", tid, request)
    session.commit()
    return {"ticket_id": tid, "status": TicketStatus.new}


@router.get("")
def list_tickets(status: str | None = Query(None, description="One status or a comma-separated list"),
                 team: str | None = None, mine: bool = False, q: str | None = None,
                 limit: int = Query(100, le=500), user: db.User = Depends(require(P.TICKETS_VIEW)),
                 session: Session = Depends(get_session)):
    search = q
    q = _scoped(select(db.Ticket), user).order_by(db.Ticket.created_at.desc()).limit(limit)
    if status:
        try:
            statuses = [TicketStatus(s.strip()) for s in status.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(422, f"Unknown status in '{status}'")
        q = q.where(db.Ticket.status.in_(statuses))
    if search:
        like = f"%{search.strip()}%"
        q = q.where(db.Ticket.subject.ilike(like) | db.Ticket.customer_email.ilike(like) | db.Ticket.id.ilike(like))
    if team:
        q = q.where(db.Ticket.team == team)
    if mine:
        q = q.where(db.Ticket.assignee_id == user.id)
    tickets = session.exec(q).all()
    ids = [t.id for t in tickets]
    triage = {r.ticket_id: r.result for r in session.exec(
        select(db.TriageRecord).where(db.TriageRecord.ticket_id.in_(ids)).order_by(db.TriageRecord.id)).all()}
    names = {u.id: u.full_name for u in session.exec(
        select(db.User).where(db.User.id.in_({t.assignee_id for t in tickets if t.assignee_id}))).all()}
    resolved: dict[str, object] = {}
    for r in session.exec(select(db.Review).where(db.Review.ticket_id.in_(ids),
                                                  db.Review.decision.in_(list(RESOLVING_DECISIONS)))).all():
        resolved[r.ticket_id] = min(resolved.get(r.ticket_id, r.created_at), r.created_at)
    return [{**t.model_dump(mode="json"),
             "category": triage.get(t.id, {}).get("category"),
             "sentiment": triage.get(t.id, {}).get("sentiment"),
             "assignee_name": names.get(t.assignee_id),
             "sla": sla_for(t.priority, t.created_at, t.status, resolved.get(t.id))} for t in tickets]


@router.get("/stats")
def stats(user: db.User = Depends(require(P.TICKETS_VIEW)), session: Session = Depends(get_session)):
    tickets = session.exec(_scoped(select(db.Ticket), user)).all()
    ids = [t.id for t in tickets]
    runs = session.exec(select(db.PipelineRun).where(db.PipelineRun.ticket_id.in_(ids))).all()
    llm = session.exec(select(db.LLMCall).where(db.LLMCall.ticket_id.in_(ids))).all()
    reviews = session.exec(select(db.Review).where(db.Review.ticket_id.in_(ids))).all()
    n_runs = max(len(runs), 1)
    return {
        "tickets": len(tickets),
        "by_status": Counter(t.status.value for t in tickets),
        "by_team": Counter(t.team or "unrouted" for t in tickets),
        "by_language": Counter(t.language or "unknown" for t in tickets),
        "avg_latency_s": round(sum(r.total_latency_ms for r in runs) / n_runs / 1000, 1),
        "avg_tokens_per_ticket": round(sum(c.input_tokens + c.output_tokens for c in llm) / n_runs),
        "reviews": Counter(r.decision for r in reviews),
        "queue": queue_depth(),
    }


@router.get("/examples")
def examples(_: db.User = Depends(require(P.TICKETS_CREATE))):
    """Sample tickets (EN/AR/Arabizi) from the eval set, for the 'new ticket' form in demos."""
    import json

    from app.config import DATA_DIR
    rows = json.loads((DATA_DIR / "eval_set.json").read_text("utf-8"))
    return [{"id": r["id"], "tags": r["tags"], **{k: r["ticket"][k] for k in ("subject", "body", "customer_email", "channel")}}
            for r in rows]


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, user: db.User = Depends(require(P.TICKETS_VIEW)),
               session: Session = Depends(get_session)):
    _get_visible(session, user, ticket_id)
    return service.ticket_detail(ticket_id)


@router.post("/{ticket_id}/review")
def review_ticket(ticket_id: str, r: ReviewIn, user: db.User = Depends(require(P.TICKETS_REVIEW)),
                  session: Session = Depends(get_session)):
    t = _get_visible(session, user, ticket_id)
    if t.status == TicketStatus.escalated and not has_permission(user.role, P.TICKETS_HANDLE_ESCALATED):
        raise HTTPException(403, "Escalated tickets can only be handled by a team lead or admin")
    if t.status not in (TicketStatus.in_review, TicketStatus.ready_to_send, TicketStatus.escalated):
        raise HTTPException(409, f"Ticket is '{t.status.value}' and can't be reviewed")
    if r.decision.value == "edit" and not (r.edited_reply or "").strip():
        raise HTTPException(422, "edited_reply is required for decision=edit")
    return service.review(ticket_id, r, user).model_dump(mode="json")


class AssignIn(BaseModel):
    team: str | None = None
    assignee_id: int | None = None


@router.post("/{ticket_id}/assign")
def assign_ticket(ticket_id: str, body: AssignIn, request: Request,
                  user: db.User = Depends(require(P.TICKETS_REASSIGN)), session: Session = Depends(get_session)):
    t = _get_visible(session, user, ticket_id)
    before = {"team": t.team, "assignee_id": t.assignee_id}
    if body.team is not None:
        if body.team not in team_names():
            raise HTTPException(422, f"Unknown team '{body.team}'")
        t.team = body.team
    if body.assignee_id is not None:
        assignee = session.get(db.User, body.assignee_id)
        if assignee is None or not assignee.is_active:
            raise HTTPException(422, "Assignee not found or inactive")
        t.assignee_id = assignee.id
    t.updated_at = db._now()
    audit(session, user, "ticket.assign", "ticket", ticket_id, request,
          before=before, after={"team": t.team, "assignee_id": t.assignee_id})
    session.commit()
    return {"ticket_id": ticket_id, "team": t.team, "assignee_id": t.assignee_id}
