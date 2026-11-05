"""Background worker: processes queued tickets through the AI pipeline.

    python -m app.worker

Run one or more alongside the API. With local CPU models one worker is right
(Ollama serves one request at a time anyway); with a cloud LLM, run several.
"""
import logging
import os
import signal
import socket
import time

from sqlmodel import Session

from app.config import get_settings
from app.db.session import engine, init_db
from app.jobs import queue
from app.models import db
from app.models.schemas import TicketIn
from app.pipeline import service

log = logging.getLogger("worker")
_running = True


def _stop(*_):
    global _running
    log.info("Shutdown requested; finishing current job...")
    _running = False


def run_once(worker_id: str) -> bool:
    """Process one job if available. Returns True if a job was processed."""
    job = queue.claim_next(worker_id)
    if job is None:
        return False
    log.info("job %s: ticket %s (attempt %s)", job.id, job.ticket_id, job.attempts)
    try:
        with Session(engine) as s:
            t = s.get(db.Ticket, job.ticket_id)
            ticket = TicketIn(subject=t.subject, body=t.body, customer_email=t.customer_email,
                              channel=t.channel, created_at=t.created_at)
        service.process_ticket(job.ticket_id, ticket, retry_transient=job.attempts < job.max_attempts)
        queue.complete(job.id)
        log.info("job %s: done", job.id)
    except Exception as e:  # transient LLM errors (retried) and infrastructure errors
        log.warning("job %s attempt %s failed: %s: %s", job.id, job.attempts, type(e).__name__, e)
        queue.fail(job.id, f"{type(e).__name__}: {e}")
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    log.info("worker %s started (poll %.1fs)", worker_id, get_settings().worker_poll_seconds)
    while _running:
        if not run_once(worker_id):
            time.sleep(get_settings().worker_poll_seconds)


if __name__ == "__main__":
    main()
