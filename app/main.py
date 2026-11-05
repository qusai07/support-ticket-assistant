import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.analytics import router as analytics_router
from app.api.events import router as events_router
from app.api.kb import router as kb_router
from app.api.monitor import router as monitor_router
from app.api.settings import router as settings_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.auth.permissions import seed_teams
from app.auth.router import router as auth_router
from app.config import get_settings
from app.db.session import init_db
from app.rag.store import KB, _collection, build_index, load_kb

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.jwt_secret == "dev-insecure-change-me":
        if s.environment == "prod":
            raise RuntimeError("JWT_SECRET must be set in production")
        log.warning("Using the default dev JWT secret. Set JWT_SECRET for any shared deployment.")
    init_db()
    seed_teams()
    load_kb()  # seeds the kb_articles table from data/ on first run
    if _collection(KB).count() == 0:  # first run (e.g. fresh Docker volume)
        build_index()
    yield


app = FastAPI(title="Support Ticket Resolution Assistant", version="0.2.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tickets_router)
app.include_router(kb_router)
app.include_router(settings_router)
app.include_router(analytics_router)
app.include_router(events_router)
app.include_router(admin_router)
app.include_router(monitor_router)


@app.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "triage_model": s.triage_model, "agent_model": s.agent_model}
