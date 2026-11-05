"""Workflow tracking and monitoring.

- /tickets/{id}/timeline : every step a ticket went through, who did it (AI, rules, a
  person, the system) and how long it took, plus its SLA status.
- /monitor/overview      : flow counts per stage, SLA health, queue/worker health,
  per-stage AI latency, team workload and a live activity feed.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.deps import can_see_ticket, require
from app.auth.permissions import Permission, has_permission
from app.db.session import get_session
from app.models import db
from app.runtime_settings import get_runtime
from app.sla import OPEN, RESOLVING_DECISIONS, sla_for, utc

router = APIRouter(tags=["monitoring"])
STAGES = ["triage", "retrieve", "route", "agent", "hitl", "escalate"]


def _resolved_at(reviews: list[db.Review]) -> datetime | None:
    done = [r.created_at for r in reviews if r.decision in RESOLVING_DECISIONS]
    return min(done) if done else None


@router.get("/tickets/{ticket_id}/timeline")
def timeline(ticket_id: str, user: db.User = Depends(require(Permission.TICKETS_VIEW)),
             session: Session = Depends(get_session)):
    t = session.get(db.Ticket, ticket_id)
    if t is None or not can_see_ticket(user, t):
        raise HTTPException(404, "ticket not found")

    def rows(model, order=None):
        return session.exec(select(model).where(model.ticket_id == ticket_id).order_by(order or model.id)).all()

    jobs, runs, escs, reviews = rows(db.Job), rows(db.PipelineRun), rows(db.Escalation), rows(db.Review)
    triage = rows(db.TriageRecord)
    tools = rows(db.ToolCallRecord, db.ToolCallRecord.seq)
    audits = session.exec(select(db.AuditLog).where(db.AuditLog.target_type == "ticket", db.AuditLog.target_id == ticket_id,
                                                    db.AuditLog.action == "ticket.assign").order_by(db.AuditLog.id)).all()
    names = {u.id: u.full_name for u in session.exec(select(db.User)).all()}
    ev: list[dict] = []
    add = lambda kind, at, actor, actor_type, detail=None, duration_ms=None: ev.append(
        {"kind": kind, "at": utc(at).isoformat(), "actor": actor, "actor_type": actor_type,
         "detail": detail or {}, "duration_ms": duration_ms})

    add("received", t.created_at, t.channel, "customer", {"channel": t.channel})
    for j in jobs:
        if j.locked_at:
            wait = int((utc(j.locked_at) - utc(j.created_at)).total_seconds() * 1000)
            add("picked_up", j.locked_at, j.locked_by or "worker", "system", {"attempts": j.attempts, "status": j.status}, wait)
        if j.status == "failed":
            add("failed", j.updated_at, "worker", "system", {"error": (j.last_error or "")[:300]})

    run = runs[-1] if runs else None
    if run:
        end = utc(run.created_at)
        cursor = end - timedelta(milliseconds=run.total_latency_ms)
        tri = triage[-1].result if triage else {}
        stage_detail = {
            "triage": {"category": tri.get("category"), "priority": tri.get("priority"), "language": tri.get("language"),
                       "signals": tri.get("urgency_signals", [])},
            "retrieve": {"documents": len(run.retrieved or [])},
            "route": {"team": (run.routing or {}).get("team"), "rules": [h["rule"] for h in (run.routing or {}).get("hits", [])],
                      "escalate": (run.routing or {}).get("escalate", False)},
            "agent": {"tool_calls": len(tools), "confidence": (run.agent_output or {}).get("confidence"),
                      "flags": run.guardrail_flags},
            "hitl": {"status": run.final_status.value, "reasons": run.status_reasons},
            "escalate": {"rules": [h["rule"] for h in (run.routing or {}).get("hits", [])]},
        }
        for stage in STAGES:
            if stage in (run.timings_ms or {}):
                ms = run.timings_ms[stage]
                cursor = cursor + timedelta(milliseconds=ms)
                add(f"ai_{stage}", cursor, "AI pipeline" if stage in ("triage", "agent") else "rules",
                    "ai" if stage in ("triage", "agent") else "rules", stage_detail.get(stage), ms)
    for e in escs:
        add("escalated", e.created_at, e.source, "human" if e.source == "reviewer" else "rules", {"reason": e.reason})
    for a in audits:
        add("assigned", a.created_at, names.get(a.user_id, "?"), "human", a.detail.get("after", {}))
    for r in reviews:
        add("reviewed", r.created_at, r.reviewer, "human", {"decision": r.decision, "comment": r.comment})

    ev.sort(key=lambda x: x["at"])
    resolved = _resolved_at(reviews)
    return {"ticket_id": ticket_id, "status": t.status.value, "events": ev,
            "sla": sla_for(t.priority, t.created_at, t.status, resolved),
            "resolved_at": utc(resolved).isoformat() if resolved else None}


@router.get("/monitor/overview")
def overview(user: db.User = Depends(require(Permission.ANALYTICS_VIEW)), session: Session = Depends(get_session)):
    q = select(db.Ticket)
    if not has_permission(user.role, Permission.TICKETS_VIEW_ALL):
        q = q.where(db.Ticket.team == user.team)
    tickets = session.exec(q).all()
    ids = [t.id for t in tickets]
    reviews_by: dict[str, list[db.Review]] = defaultdict(list)
    for r in session.exec(select(db.Review).where(db.Review.ticket_id.in_(ids))).all():
        reviews_by[r.ticket_id].append(r)
    runs = session.exec(select(db.PipelineRun).where(db.PipelineRun.ticket_id.in_(ids))).all()
    jobs = session.exec(select(db.Job).where(db.Job.ticket_id.in_(ids))).all()
    now = datetime.now(timezone.utc)

    # ---- flow: where tickets are and where they went
    status = Counter(t.status.value for t in tickets)
    first_route = {r.ticket_id: r.final_status.value for r in runs}  # where the AI sent it
    decisions = Counter(rv.decision for rs in reviews_by.values() for rv in rs if rv.decision in RESOLVING_DECISIONS)
    # Each ticket's path: AI outcome (or still processing) -> final outcome (or still open).
    outcome_name = {"approve": "approved", "edit": "edited", "reject": "rejected"}
    links: Counter = Counter()
    for t in tickets:
        src = first_route.get(t.id, "processing")
        resolving = [r for r in sorted(reviews_by[t.id], key=lambda r: r.created_at) if r.decision in RESOLVING_DECISIONS]
        dst = outcome_name[resolving[-1].decision] if resolving else "open"
        links[(src, dst)] += 1
    flow = {
        "received": len(tickets),
        "processing": status["new"] + status["triaged"],
        "routed": dict(Counter(first_route.values())),         # escalated / in_review / ready_to_send
        "current": dict(status),
        "resolved": {"approved": decisions["approve"], "edited": decisions["edit"], "rejected": decisions["reject"]},
        "links": [{"from": a, "to": b, "n": n} for (a, b), n in sorted(links.items())],
    }

    # ---- SLA
    sla_rows, at_risk = defaultdict(Counter), []
    for t in tickets:
        s = sla_for(t.priority, t.created_at, t.status, _resolved_at(reviews_by[t.id]), now)
        sla_rows[t.priority or "P3"][s["state"]] += 1
        if s["state"] in ("at_risk", "breached"):
            at_risk.append({"id": t.id, "subject": t.subject, "priority": t.priority, "team": t.team,
                            "status": t.status.value, "language": t.language, **s})
    at_risk.sort(key=lambda x: -x["fraction"])
    hours = get_runtime()["sla_hours"]
    sla = [{"priority": p, "target_hours": hours[p], **{k: sla_rows[p][k] for k in ("on_track", "at_risk", "breached", "met", "missed")}}
           for p in ("P1", "P2", "P3", "P4")]

    # ---- queue / worker health
    jstat = Counter(j.status for j in jobs)
    queued = [j for j in jobs if j.status == "queued"]
    running = [j for j in jobs if j.status == "running"]
    oldest_wait = max(((now - utc(j.created_at)).total_seconds() for j in queued), default=0)
    longest_run = max(((now - utc(j.locked_at)).total_seconds() for j in running if j.locked_at), default=0)
    last_done = max((utc(j.updated_at) for j in jobs if j.status == "done"), default=None)
    queue = {"queued": jstat["queued"], "running": jstat["running"], "done": jstat["done"], "failed": jstat["failed"],
             "oldest_wait_s": int(oldest_wait), "longest_running_s": int(longest_run),
             "workers": sorted({j.locked_by for j in running if j.locked_by}),
             "last_completed_at": last_done.isoformat() if last_done else None}

    # ---- per-stage AI latency
    by_stage: dict[str, list[int]] = defaultdict(list)
    for r in runs:
        for k, v in (r.timings_ms or {}).items():
            by_stage[k].append(v)
    stages = [{"stage": k, "avg_ms": int(mean(v)), "p95_ms": sorted(v)[min(len(v) - 1, int(0.95 * len(v)))], "n": len(v)}
              for k in STAGES if (v := by_stage.get(k))]

    # ---- team workload
    workload = defaultdict(lambda: {"open": 0, "oldest_open_s": 0, "breached": 0})
    for t in tickets:
        if t.status in OPEN:
            w = workload[t.team or "unrouted"]
            w["open"] += 1
            w["oldest_open_s"] = max(w["oldest_open_s"], int((now - utc(t.created_at)).total_seconds()))
            if sla_for(t.priority, t.created_at, t.status, None, now)["state"] == "breached":
                w["breached"] += 1
    teams = sorted(({"team": k, **v} for k, v in workload.items()), key=lambda x: -x["open"])

    # ---- activity feed
    acts = []
    for r in runs:
        acts.append({"at": utc(r.created_at).isoformat(), "kind": "ai_done", "ticket_id": r.ticket_id, "detail": r.final_status.value})
    for rs in reviews_by.values():
        for r in rs:
            acts.append({"at": utc(r.created_at).isoformat(), "kind": "reviewed", "ticket_id": r.ticket_id,
                         "detail": r.decision, "actor": r.reviewer})
    for t in tickets:
        acts.append({"at": utc(t.created_at).isoformat(), "kind": "received", "ticket_id": t.id, "detail": t.channel})
    acts.sort(key=lambda a: a["at"], reverse=True)

    return {"flow": flow, "sla": sla, "at_risk": at_risk[:15], "queue": queue, "stages": stages,
            "teams": teams, "activity": acts[:25], "open": sum(1 for t in tickets if t.status in OPEN),
            "generated_at": now.isoformat()}
