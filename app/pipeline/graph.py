"""LangGraph workflow.

    triage -> retrieve -> route --(rule hit)--> escalate -> END
                               \--(clear)---> agent -> hitl -> END

The graph only orchestrates. Each node is a plain function from pipeline/ or
agent/, so it can be unit-tested without LangGraph.
"""
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.agent import AgentResult, run_agent
from app.models.enums import TicketStatus
from app.models.schemas import RetrievedDoc, RoutingDecision, TicketIn, TriageResult
from app.pipeline.hitl import gate
from app.pipeline.retrieval import retrieve
from app.pipeline.routing import escalation_summary, route
from app.pipeline.triage import triage


class TicketState(TypedDict, total=False):
    ticket_id: str
    ticket: TicketIn
    triage: TriageResult
    docs: list[RetrievedDoc]
    routing: RoutingDecision
    agent: AgentResult
    status: TicketStatus
    status_reasons: list[str]
    escalation: dict
    timings_ms: dict[str, int]


def _timed(name: str, fn):
    def node(state: TicketState) -> dict[str, Any]:
        t0 = time.perf_counter()
        update = fn(state)
        timings = dict(state.get("timings_ms", {}))
        timings[name] = int((time.perf_counter() - t0) * 1000)
        return {**update, "timings_ms": timings}
    return node


def _triage(s: TicketState):
    return {"triage": triage(s["ticket"])}


def _retrieve(s: TicketState):
    return {"docs": retrieve(s["ticket"], s["triage"].language)}


def _route(s: TicketState):
    return {"routing": route(s["ticket"], s["triage"])}


def _escalate(s: TicketState):
    reason = ", ".join(h.rule for h in s["routing"].hits)
    return {"status": TicketStatus.escalated, "status_reasons": [h.detail for h in s["routing"].hits],
            "escalation": {"reason": reason, "summary": escalation_summary(s["ticket"], s["triage"], s["routing"]),
                           "source": "routing_rules"}}


def _agent(s: TicketState):
    return {"agent": run_agent(s["ticket_id"], s["ticket"], s["triage"], s["docs"])}


def _hitl(s: TicketState):
    status, reasons = gate(s["triage"], s["agent"])
    update: dict[str, Any] = {"status": status, "status_reasons": reasons}
    if status == TicketStatus.escalated:
        esc = s["agent"].escalations[0] if s["agent"].escalations else {}
        update["escalation"] = {"reason": esc.get("reason", "agent escalated"),
                                "summary": esc.get("summary", s["agent"].output.draft_reply), "source": "agent"}
    return update


def build_graph():
    g = StateGraph(TicketState)
    for name, fn in [("triage", _triage), ("retrieve", _retrieve), ("route", _route),
                     ("escalate", _escalate), ("agent", _agent), ("hitl", _hitl)]:
        g.add_node(name, _timed(name, fn))
    g.set_entry_point("triage")
    g.add_edge("triage", "retrieve")
    g.add_edge("retrieve", "route")
    g.add_conditional_edges("route", lambda s: "escalate" if s["routing"].escalate else "agent",
                            {"escalate": "escalate", "agent": "agent"})
    g.add_edge("escalate", END)
    g.add_edge("agent", "hitl")
    g.add_edge("hitl", END)
    return g.compile()


GRAPH = build_graph()
