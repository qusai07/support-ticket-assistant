"""Quick manual check of triage on a few eval tickets.

    python -m scripts.try_triage EV-01 EV-30 EV-46
"""
import json
import sys
import time

from app.config import DATA_DIR
from app.llm.client import track_usage
from app.models.schemas import LabeledTicket
from app.pipeline.triage import triage

ids = set(sys.argv[1:]) or {"EV-01", "EV-30", "EV-46"}
cases = [LabeledTicket.model_validate(x) for x in json.loads((DATA_DIR / "eval_set.json").read_text("utf-8"))]
selected = cases if "all" in ids else [c for c in cases if c.id in ids]
n_cat = n_pri = 0

for case in selected:
    with track_usage() as calls:
        t0 = time.perf_counter()
        r = triage(case.ticket)
        dt = time.perf_counter() - t0
    ok_c = "OK " if r.category == case.expected_category else "BAD"
    ok_p = "OK " if r.priority == case.expected_priority else "BAD"
    print(f"\n{case.id}  ({dt:.1f}s, {sum(c.output_tokens for c in calls)} out tokens)")
    print(f"  category {ok_c} got={r.category.value:<10} expected={case.expected_category.value}")
    print(f"  priority {ok_p} got={r.priority.value:<10} expected={case.expected_priority.value}")
    print(f"  sentiment={r.sentiment.value} ({r.sentiment_score}) signals={r.urgency_signals}")
    print(f"  entities={r.entities.model_dump()} missing={r.missing_info} injection={r.injection_suspected}")
    n_cat += r.category == case.expected_category
    n_pri += r.priority == case.expected_priority

print(f"\nCATEGORY {n_cat}/{len(selected)}   PRIORITY {n_pri}/{len(selected)}")
