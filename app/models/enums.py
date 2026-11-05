from enum import Enum


class Category(str, Enum):
    billing = "billing"
    shipping = "shipping"
    technical = "technical"
    account = "account"
    refund = "refund"
    other = "other"


class Priority(str, Enum):
    P1 = "P1"  # critical: legal, fraud, outage, safety
    P2 = "P2"  # high: money wrong, customer blocked
    P3 = "P3"  # normal
    P4 = "P4"  # low: questions, feedback


class Channel(str, Enum):
    email = "email"
    chat = "chat"
    web_form = "web_form"
    phone = "phone"


class Sentiment(str, Enum):
    very_negative = "very_negative"
    negative = "negative"
    neutral = "neutral"
    positive = "positive"


class RecommendedAction(str, Enum):
    send = "send"
    human_review = "human_review"
    escalate = "escalate"


class TicketStatus(str, Enum):
    new = "new"
    triaged = "triaged"
    escalated = "escalated"
    ready_to_send = "ready_to_send"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    sent = "sent"


class ReviewDecision(str, Enum):
    approve = "approve"
    edit = "edit"
    reject = "reject"
    escalate = "escalate"


class OrderStatus(str, Enum):
    processing = "processing"
    shipped = "shipped"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"
    returned = "returned"
    lost = "lost"


class Plan(str, Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"
