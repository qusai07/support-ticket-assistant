"""DB-backed job queue.

Claiming is a compare-and-set UPDATE:
    UPDATE jobs SET status='running', ... WHERE id=:id AND <still claimable>
If two workers race for the same job, only one UPDATE matches a row. This works
the same on SQLite and Postgres (no SKIP LOCKED needed at this scale).

Crash recovery: a job stuck in 'running' longer than job_lock_timeout_s (worker
died, machine rebooted) becomes claimable again. After max_attempts it fails, and
the ticket goes to human review: fail to human, never lose a ticket.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, update
from sqlmodel import Session, select

from app.config import get_settings
from app.db.session import engine
from app.models import db
from app.models.enums import TicketStatus


def _claimable(cutoff: datetime):
    J = db.Job
    return or_(J.status == "queued", and_(J.status == "running", J.locked_at < cutoff))


def claim_next(worker_id: str) -> db.Job | None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=get_settings().job_lock_timeout_s)
    with Session(engine) as s:
        candidates = s.exec(select(db.Job.id).where(_claimable(cutoff)).order_by(db.Job.id).limit(5)).all()
        for job_id in candidates:
            res = s.execute(
                update(db.Job)
                .where(db.Job.id == job_id, _claimable(cutoff))
                .values(status="running", locked_by=worker_id, locked_at=now,
                        attempts=db.Job.attempts + 1, updated_at=now))
            s.commit()
            if res.rowcount == 1:
                return s.get(db.Job, job_id)
    return None


def complete(job_id: int) -> None:
    with Session(engine) as s:
        job = s.get(db.Job, job_id)
        job.status, job.updated_at, job.locked_by = "done", db._now(), None
        s.commit()


def fail(job_id: int, error: str) -> None:
    with Session(engine) as s:
        job = s.get(db.Job, job_id)
        job.last_error, job.updated_at, job.locked_by = error[:2000], db._now(), None
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            ticket = s.get(db.Ticket, job.ticket_id)
            if ticket and ticket.status == TicketStatus.new:
                ticket.status, ticket.team = TicketStatus.in_review, ticket.team or "Customer Care"
                ticket.updated_at = db._now()
        else:
            job.status = "queued"
        s.commit()


def queue_depth() -> dict[str, int]:
    with Session(engine) as s:
        rows = s.exec(select(db.Job.status)).all()
    out: dict[str, int] = {}
    for status in rows:
        out[status] = out.get(status, 0) + 1
    return out
