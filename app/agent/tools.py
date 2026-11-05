"""Agent tools. A ToolBox is created per ticket and scoped to that ticket's customer.

Security model: the LLM chooses WHICH tool to call, but cannot widen WHOSE data
it sees. get_customer/get_order/check_refund_eligibility only return data that
belongs to the email on the ticket. A prompt injection asking for another
customer's order gets {"error": "access_denied"}.
"""
import json
import time
from typing import Any, Callable

from app.models.schemas import ToolCall
from app.rag.store import search_kb as _search_kb
from app.services import mock_backend as backend

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "get_customer",
        "description": "Look up the customer who sent this ticket: plan, tenure, VIP flag, membership renewal date, their order IDs and recent tickets.",
        "parameters": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}},
    {"type": "function", "function": {
        "name": "get_order",
        "description": "Get an order's status, items, prices, tracking (carrier, number, ETA), delivery date and payment details.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "e.g. ORD-10001"}},
                       "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "search_kb",
        "description": "Search Lumora help-center articles (policies and how-tos). Returns article IDs to cite.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "check_refund_eligibility",
        "description": "Apply the official refund policy to an order. ALWAYS call this before saying anything about refunds, returns or cancellations.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "create_escalation",
        "description": "Hand the ticket to a human specialist. ONLY use when the request needs an action you cannot take: reshipping a lost package, opening a carrier trace, identity verification, or account security. Do NOT use for normal returns, refunds, cancellations or questions; those are answered with a draft that a human reviews anyway.",
        "parameters": {"type": "object", "properties": {
            "ticket_id": {"type": "string"}, "reason": {"type": "string"}, "summary": {"type": "string"}},
            "required": ["ticket_id", "reason", "summary"]}}},
]


class ToolBox:
    def __init__(self, ticket_id: str, customer_email: str, kb_lang: str = "en"):
        self.ticket_id = ticket_id
        self.email = customer_email.lower().strip()
        self.kb_lang = kb_lang
        self.trace: list[ToolCall] = []
        self.escalations: list[dict] = []
        self._impl: dict[str, Callable[..., Any]] = {
            "get_customer": self.get_customer,
            "get_order": self.get_order,
            "search_kb": self.search_kb,
            "check_refund_eligibility": self.check_refund_eligibility,
            "create_escalation": self.create_escalation,
        }

    # ---- dispatch
    def call(self, name: str, args: dict, step: str = "agent") -> Any:
        started = time.perf_counter()
        result, error = None, None
        try:
            if name not in self._impl:
                raise ValueError(f"unknown tool {name}")
            result = self._impl[name](**(args or {}))
        except TypeError as e:
            error = f"bad arguments: {e}"
        except Exception as e:  # tool failures are reported to the model, never crash the run
            error = str(e)
        self.trace.append(ToolCall(step=step, tool=name, args=args or {}, result=result, error=error,
                                   latency_ms=int((time.perf_counter() - started) * 1000)))
        return result if error is None else {"error": error}

    # ---- helpers
    def _owned_order(self, order_id: str):
        order = backend.find_order(order_id)
        if order is None:
            return None, {"error": "order_not_found", "order_id": order_id}
        cust = backend.find_customer(self.email)
        if cust is None or order.customer_id != cust.id:
            return None, {"error": "access_denied", "detail": "Order does not belong to the ticket's customer."}
        return order, None

    # ---- tools
    def get_customer(self, email: str = "") -> dict:
        if email and email.lower().strip() != self.email:
            return {"error": "access_denied", "detail": "Can only look up the customer who sent this ticket."}
        cust = backend.find_customer(self.email)
        return backend.customer_summary(cust) if cust else {"error": "customer_not_found", "email": self.email}

    def get_order(self, order_id: str) -> dict:
        order, err = self._owned_order(order_id)
        return err or order.model_dump(mode="json")

    def search_kb(self, query: str) -> list[dict]:
        return [{"id": d.source_id, "title": d.title, "text": d.snippet}
                for d in _search_kb(query, k=3, lang=self.kb_lang)]

    def check_refund_eligibility(self, order_id: str) -> dict:
        order, err = self._owned_order(order_id)
        return err or backend.check_refund_eligibility(order)

    def create_escalation(self, ticket_id: str = "", reason: str = "", summary: str = "") -> dict:
        # ticket_id from the model is ignored: we always escalate THIS ticket.
        self.escalations.append({"ticket_id": self.ticket_id, "reason": reason, "summary": summary})
        return {"status": "queued_for_human", "ticket_id": self.ticket_id}

    # ---- for groundedness checks
    def observed_text(self) -> str:
        return json.dumps([c.result for c in self.trace if c.result is not None], default=str)
