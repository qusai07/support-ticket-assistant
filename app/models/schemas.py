"""Pydantic schemas: API contracts, LLM structured outputs, and domain data.

Rule of thumb: anything an LLM produces gets a schema here, and we validate it.
An LLM output that fails validation is a bug we can count in evals, not a silent
corruption that leaks into a customer reply."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import (
    Category,
    Channel,
    OrderStatus,
    Plan,
    Priority,
    RecommendedAction,
    ReviewDecision,
    Sentiment,
)

# ---------- Intake ----------


class TicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10_000)
    customer_email: EmailStr
    channel: Channel = Channel.email
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------- Triage ----------


class Entities(BaseModel):
    order_ids: list[str] = []
    products: list[str] = []
    dates: list[str] = []
    amounts: list[float] = []


Language = Literal["en", "ar", "mixed", "ar_latn"]


class TriageResult(BaseModel):
    language: Language = "en"
    category: Category
    secondary_categories: list[Category] = []
    priority: Priority
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    urgency_signals: list[str] = []
    entities: Entities = Entities()
    missing_info: list[str] = []
    injection_suspected: bool = False
    rationale: str = ""


# ---------- Retrieval & routing ----------


class RetrievedDoc(BaseModel):
    source_id: str
    source_type: Literal["kb", "past_ticket"]
    lang: str = "en"
    title: str
    snippet: str
    score: float


class RuleHit(BaseModel):
    rule: str
    detail: str


class RoutingDecision(BaseModel):
    escalate: bool
    hits: list[RuleHit] = []
    team: str = "Customer Care"  # the queue that owns the ticket (escalated or reviewed)


# ---------- Agent ----------


class ToolCall(BaseModel):
    step: str = "agent"  # "prefetch" (pipeline-initiated) or "agent" (model-initiated)
    tool: str
    args: dict
    result: dict | list | None = None
    error: str | None = None
    latency_ms: int = 0


class AgentOutput(BaseModel):
    draft_reply: str
    clarifying_question: str | None = None
    actions_taken: list[str] = []
    sources: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: RecommendedAction


# ---------- Review ----------


class ReviewIn(BaseModel):
    decision: ReviewDecision
    edited_reply: str | None = None
    reviewer: str = "reviewer"
    comment: str | None = None


# ---------- Domain (mock backend) ----------


class OrderItem(BaseModel):
    sku: str
    name: str
    qty: int
    unit_price: float


class Payment(BaseModel):
    method: Literal["card", "paypal", "bank_transfer"]
    status: Literal["paid", "pending", "failed", "refunded", "partially_refunded"]
    charged_count: int = 1
    amount: float


class Tracking(BaseModel):
    carrier: str | None = None
    number: str | None = None
    eta: str | None = None


class Order(BaseModel):
    id: str
    customer_id: str
    status: OrderStatus
    items: list[OrderItem]
    total: float
    payment: Payment
    tracking: Tracking
    created_at: str
    delivered_at: str | None = None


class Customer(BaseModel):
    id: str
    email: EmailStr
    name: str
    plan: Plan
    tenure_months: int
    is_vip: bool
    plan_renewed_at: str | None = None
    order_ids: list[str] = []
    past_ticket_ids: list[str] = []


class KBArticle(BaseModel):
    id: str
    title: str
    category: Category
    body: str
    title_ar: str = ""
    body_ar: str = ""
    policy_tags: list[str] = []


class HistoricalTicket(BaseModel):
    id: str
    subject: str
    body: str
    category: Category
    priority: Priority
    customer_email: EmailStr
    resolution: str
    kb_refs: list[str] = []


# ---------- Eval ----------


class LabeledTicket(BaseModel):
    id: str
    ticket: TicketIn
    expected_category: Category
    expected_priority: Priority
    expected_action: RecommendedAction
    tags: list[str] = []
    notes: str = ""
