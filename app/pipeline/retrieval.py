"""Workflow retrieval step: runs for every ticket, before routing and the agent.

The query is the ticket text itself (any language: bge-m3 is cross-lingual).
KB articles come back in the customer's language. The agent can run more targeted
searches later through the `search_kb` tool.
"""
from app.models.schemas import RetrievedDoc, TicketIn
from app.rag.store import search_kb, search_past_tickets


def kb_lang(language: str) -> str:
    return "ar" if language in ("ar", "mixed") else "en"


def retrieve(ticket: TicketIn, language: str = "en", k_kb: int = 3, k_past: int = 3) -> list[RetrievedDoc]:
    query = f"{ticket.subject}\n{ticket.body}"
    return search_kb(query, k_kb, lang=kb_lang(language)) + search_past_tickets(query, k_past)
