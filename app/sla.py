"""SLA: time-to-resolution targets per priority. Pure functions, no LLM.

A ticket is OPEN until a reviewer approves, edits or rejects it (an "escalate" review
keeps it open: it moved, it wasn't resolved). Its clock starts at creation.
"""
from datetime import datetime, timedelta, timezone

from app.models.enums import TicketStatus
from app.runtime_settings import DEFAULT_SLA_HOURS, SLA_AT_RISK_FRACTION, get_runtime

OPEN = {TicketStatus.new, TicketStatus.triaged, TicketStatus.in_review, TicketStatus.escalated, TicketStatus.ready_to_send}
RESOLVING_DECISIONS = {"approve", "edit", "reject"}


def utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def sla_for(priority: str | None, created_at: datetime, status: TicketStatus,
            resolved_at: datetime | None = None, now: datetime | None = None) -> dict:
    """Returns target, due time and state: on_track | at_risk | breached | met | missed."""
    hours = (get_runtime().get("sla_hours") or DEFAULT_SLA_HOURS).get(priority or "P3", DEFAULT_SLA_HOURS["P3"])
    created = utc(created_at)
    due = created + timedelta(hours=hours)
    now = now or datetime.now(timezone.utc)
    if status in OPEN or resolved_at is None:
        elapsed = (now - created).total_seconds()
        frac = elapsed / (hours * 3600)
        state = "breached" if frac >= 1 else "at_risk" if frac >= SLA_AT_RISK_FRACTION else "on_track"
    else:
        resolved = utc(resolved_at)
        elapsed = (resolved - created).total_seconds()
        frac = elapsed / (hours * 3600)
        state = "met" if resolved <= due else "missed"
    return {"target_hours": hours, "due_at": due.isoformat(), "elapsed_s": int(elapsed),
            "fraction": round(frac, 3), "state": state}
