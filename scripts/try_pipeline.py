"""Run the full graph on eval tickets and print the outcome.

    python -m scripts.try_pipeline EV-01 EV-20 EV-40
"""
import json
import sys
import time

from app.config import DATA_DIR
from app.llm.client import track_usage
from app.models.schemas import LabeledTicket
from app.pipeline.graph import GRAPH
from app.pipeline.hitl import STATUS_TO_ACTION

ids = sys.argv[1:] or ["EV-01", "EV-20", "EV-40"]
cases = {c["id"]: LabeledTicket.model_validate(c) for c in json.loads((DATA_DIR / "eval_set.json").read_text("utf-8"))}

for cid in ids:
    case = cases[cid]
    with track_usage() as calls:
        t0 = time.perf_counter()
        s = GRAPH.invoke({"ticket_id": cid, "ticket": case.ticket})
        dt = time.perf_counter() - t0
    action = STATUS_TO_ACTION[s["status"]]
    mark = "OK " if action == case.expected_action else "BAD"
    print(f"\n{'=' * 80}\n{cid} [{mark}] action={action.value} expected={case.expected_action.value}  "
          f"({dt:.1f}s, {len(calls)} LLM calls, "
          f"tokens in/out {sum(c.input_tokens for c in calls)}/{sum(c.output_tokens for c in calls)}, "
          f"per-call ms {[c.latency_ms for c in calls]})")
    print(f"  ticket: {case.ticket.body[:110]}")
    print(f"  triage: {s['triage'].category.value}/{s['triage'].priority.value} {s['triage'].sentiment.value}")
    print(f"  reasons: {s.get('status_reasons')}")
    if "agent" in s:
        a = s["agent"]
        for c in a.trace:
            print(f"  tool[{c.step}]: {c.tool}({c.args}) -> {'ERR ' + c.error if c.error else str(c.result)[:120]}")
        print(f"  confidence: raw={a.raw_confidence} calibrated={a.output.confidence} flags={a.guardrail_flags}")
        print(f"  sources: {a.output.sources}")
        print("  draft:\n    " + a.output.draft_reply.replace("\n", "\n    "))
    if "escalation" in s:
        print("  escalation:\n    " + s["escalation"]["summary"].replace("\n", "\n    "))
