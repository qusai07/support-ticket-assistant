"""SQLModel tables. Structured LLM outputs are stored as JSON columns: we keep
the exact payload the model produced, which is what evals and audits need."""
from datetime import datetime, timezone

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.enums import TicketStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Store every timestamp timezone-aware in UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"
    id: str = Field(primary_key=True)
    subject: str
    body: str
    customer_email: str = Field(index=True)
    channel: str
    created_at: datetime
    status: TicketStatus = Field(default=TicketStatus.new, index=True)
    team: str | None = Field(default=None, index=True)          # owning queue, set by routing
    assignee_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    language: str | None = None
    priority: str | None = Field(default=None, index=True)
    updated_at: datetime = Field(default_factory=_now)


class TriageRecord(SQLModel, table=True):
    __tablename__ = "triage_results"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    result: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_runs"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    retrieved: list = Field(default_factory=list, sa_column=Column(JSON))
    routing: dict = Field(default_factory=dict, sa_column=Column(JSON))
    agent_output: dict | None = Field(default=None, sa_column=Column(JSON))
    status_reasons: list = Field(default_factory=list, sa_column=Column(JSON))
    guardrail_flags: list = Field(default_factory=list, sa_column=Column(JSON))
    raw_confidence: float | None = None
    timings_ms: dict = Field(default_factory=dict, sa_column=Column(JSON))
    final_status: TicketStatus
    total_latency_ms: int = 0
    created_at: datetime = Field(default_factory=_now)


class ToolCallRecord(SQLModel, table=True):
    __tablename__ = "tool_calls"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    seq: int
    step: str  # prefetch | agent
    tool: str
    args: dict = Field(sa_column=Column(JSON))
    result: dict | list | None = Field(default=None, sa_column=Column(JSON))
    error: str | None = None
    latency_ms: int = 0


class LLMCall(SQLModel, table=True):
    """One row per model call. With local models cost is $0, so we track tokens
    and latency, plus an *estimated* cloud-equivalent cost for comparison."""

    __tablename__ = "llm_calls"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str | None = Field(default=None, index=True)
    purpose: str  # triage | agent | judge
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=_now)


class Escalation(SQLModel, table=True):
    __tablename__ = "escalations"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    reason: str
    summary: str
    source: str  # "routing_rules" | "agent"
    resolved: bool = False
    created_at: datetime = Field(default_factory=_now)


class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    decision: str
    original_reply: str
    final_reply: str | None = None
    reviewer: str
    reviewer_id: int | None = Field(default=None, foreign_key="users.id")
    comment: str | None = None
    created_at: datetime = Field(default_factory=_now)


# ------------------------------------------------------------------ auth & ops


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    password_hash: str
    role: str  # app.auth.permissions.Role
    team: str | None = Field(default=None, index=True)
    preferred_language: str = "en"  # UI language: en | ar
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    last_login_at: datetime | None = None


class RefreshToken(SQLModel, table=True):
    """Only the SHA-256 of the token is stored: a DB leak doesn't leak usable tokens."""
    __tablename__ = "refresh_tokens"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    action: str = Field(index=True)       # e.g. auth.login, ticket.review, user.update
    target_type: str | None = None
    target_id: str | None = None
    detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    ip: str | None = None
    created_at: datetime = Field(default_factory=_now, index=True)


class KbArticleRow(SQLModel, table=True):
    """The knowledge base, editable from the UI. Chroma holds embeddings of these rows."""
    __tablename__ = "kb_articles"
    id: str = Field(primary_key=True)  # KB-001
    category: str = Field(index=True)
    title: str
    body: str
    title_ar: str = ""
    body_ar: str = ""
    policy_tags: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_by: int | None = Field(default=None, foreign_key="users.id")
    updated_at: datetime = Field(default_factory=_now)


class AppSetting(SQLModel, table=True):
    """Admin-editable runtime settings (thresholds, models). Overrides env defaults."""
    __tablename__ = "app_settings"
    key: str = Field(primary_key=True)
    value: dict = Field(sa_column=Column(JSON))  # {"v": <value>}
    updated_by: int | None = Field(default=None, foreign_key="users.id")
    updated_at: datetime = Field(default_factory=_now)


class TeamRow(SQLModel, table=True):
    """Teams (queues). Names are stable identifiers stored on tickets and users."""
    __tablename__ = "teams"
    name: str = Field(primary_key=True)
    name_ar: str = ""
    description: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class RolePermissions(SQLModel, table=True):
    """Admin-edited permission sets per role. Missing row = code defaults."""
    __tablename__ = "role_permissions"
    role: str = Field(primary_key=True)
    permissions: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_by: int | None = Field(default=None, foreign_key="users.id")
    updated_at: datetime = Field(default_factory=_now)


class Job(SQLModel, table=True):
    """DB-backed job queue (no Redis). Written in the same transaction as the ticket
    (outbox pattern), claimed by workers with an atomic conditional UPDATE."""
    __tablename__ = "jobs"
    id: int | None = Field(default=None, primary_key=True)
    kind: str = "process_ticket"
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    status: str = Field(default="queued", index=True)  # queued | running | done | failed
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    locked_by: str | None = None
    locked_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
