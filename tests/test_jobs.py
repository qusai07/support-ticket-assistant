"""Job queue: atomic claiming, crash recovery, fail-to-human (no LLM)."""
from datetime import timedelta

from sqlmodel import Session, select

from app.db.session import engine, init_db
from app.jobs import queue
from app.models import db
from app.models.enums import TicketStatus


def _ticket(tid: str) -> None:
    init_db()
    with Session(engine) as s:
        s.add(db.Ticket(id=tid, subject="s", body="b", customer_email="c@x.example", channel="email",
                        created_at=db._now()))
        s.add(db.Job(ticket_id=tid))
        s.commit()


def _drain_others(keep: str):
    """Other tests may have left jobs; mark them done so claim order is predictable."""
    with Session(engine) as s:
        for j in s.exec(select(db.Job).where(db.Job.ticket_id != keep, db.Job.status != "done")).all():
            j.status = "done"
        s.commit()


def test_claim_is_exclusive():
    _ticket("TCK-JOB1")
    _drain_others("TCK-JOB1")
    first = queue.claim_next("w1")
    assert first and first.ticket_id == "TCK-JOB1" and first.status == "running"
    assert queue.claim_next("w2") is None          # already claimed by w1
    queue.complete(first.id)


def test_stale_lock_is_reclaimed():
    _ticket("TCK-JOB2")
    _drain_others("TCK-JOB2")
    job = queue.claim_next("dead-worker")
    with Session(engine) as s:                     # simulate a worker that died long ago
        j = s.get(db.Job, job.id)
        j.locked_at = db._now() - timedelta(hours=2)
        s.commit()
    again = queue.claim_next("w2")
    assert again and again.id == job.id and again.attempts == 2
    queue.complete(again.id)


def test_transient_errors_are_retried_then_go_to_human(monkeypatch):
    """LLM timeouts are retried by the queue; the last attempt fails to a human."""
    import httpx

    from app import worker
    from app.pipeline import service

    def slow_llm(*a, **k):
        raise httpx.ReadTimeout("model busy")
    monkeypatch.setattr(service.GRAPH, "invoke", slow_llm)
    _ticket("TCK-JOB4")
    _drain_others("TCK-JOB4")
    for attempt in (1, 2):                       # attempts 1-2: re-queued, ticket untouched
        assert worker.run_once("w")
        with Session(engine) as s:
            j = s.exec(select(db.Job).where(db.Job.ticket_id == "TCK-JOB4")).one()
            assert j.status == "queued" and j.attempts == attempt
            assert s.get(db.Ticket, "TCK-JOB4").status == TicketStatus.new
    assert worker.run_once("w")                  # attempt 3: fail to human with the reason
    with Session(engine) as s:
        run = s.exec(select(db.PipelineRun).where(db.PipelineRun.ticket_id == "TCK-JOB4")).one()
        assert s.get(db.Ticket, "TCK-JOB4").status == TicketStatus.in_review
        assert "ReadTimeout" in run.status_reasons[0]


def test_fail_to_human_after_max_attempts():
    _ticket("TCK-JOB3")
    _drain_others("TCK-JOB3")
    for _ in range(3):
        job = queue.claim_next("w")
        queue.fail(job.id, "boom")
    with Session(engine) as s:
        assert s.get(db.Job, job.id).status == "failed"
        t = s.get(db.Ticket, "TCK-JOB3")
        assert t.status == TicketStatus.in_review and t.team == "Customer Care"
