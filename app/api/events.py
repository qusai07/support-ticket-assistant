"""Live updates via Server-Sent Events.

The worker is a separate process, so the API can't get in-memory callbacks from
it. Instead each SSE connection polls the DB cheaply (one indexed query every
2 s) for tickets changed since the last check, scoped to what this user may see.
Simple, multi-process safe, no message broker. A Postgres LISTEN/NOTIFY upgrade
can replace the polling later without changing the client.
"""
import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.auth.deps import require
from app.auth.permissions import Permission, has_permission
from app.db.session import engine
from app.models import db

router = APIRouter(tags=["events"])
POLL_S = 2.0


def _changes(user: db.User, since: datetime) -> list[dict]:
    with Session(engine) as s:
        q = select(db.Ticket).where(db.Ticket.updated_at > since)
        if not has_permission(user.role, Permission.TICKETS_VIEW_ALL):
            q = q.where((db.Ticket.team == user.team) | (db.Ticket.assignee_id == user.id))
        return [{"id": t.id, "status": t.status.value, "team": t.team, "priority": t.priority,
                 "updated_at": t.updated_at.isoformat()} for t in s.exec(q).all()]


@router.get("/events")
async def events(request: Request, user: db.User = Depends(require(Permission.TICKETS_VIEW))):
    async def stream():
        since = datetime.now(timezone.utc)
        yield "event: hello\ndata: {}\n\n"
        ticks = 0
        while not await request.is_disconnected():
            await asyncio.sleep(POLL_S)
            checked = datetime.now(timezone.utc)
            changed = await asyncio.to_thread(_changes, user, since)
            since = checked
            if changed:
                yield f"event: tickets\ndata: {json.dumps(changed)}\n\n"
            ticks += 1
            if ticks % 15 == 0:
                yield ": keep-alive\n\n"  # comment line keeps proxies from closing the stream

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
