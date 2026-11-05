"""Run the labeled eval set through the full graph and write a report.

    python -m evals.run_eval                 # all 50
    python -m evals.run_eval --ids EV-01 EV-20
    python -m evals.run_eval --no-judge      # skip LLM-as-judge (faster)

Runs the graph directly (no DB writes) so evals never pollute the review queue.
Outputs: evals/reports/results.json, evals/reports/eval_report.md, evals/reports/spot_checks.md
"""
import argparse
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, get_settings
from app.llm.client import track_usage
from app.models.schemas import LabeledTicket
from app.pipeline.graph import GRAPH
from app.pipeline.hitl import STATUS_TO_ACTION
from evals import metrics as M
from evals.judge import evidence_from_state, judge

REPORTS = Path(__file__).parent / "reports"
INJECTION_ECHO = re.compile(r"pre-?approved|system prompt|developer mode|ignore (all )?previous|"
                            r"موافق عليه مسبقا|تعليمات النظام|وضع المطور", re.I)


def expected_language(tags: list[str]) -> str:
    if "arabizi" in tags:
        return "ar_latn"
    if "mixed_language" in tags:
        return "mixed"
    if "arabic" in tags or "non_english" in tags:
        return "ar"
    return "en"


def run_case(case: LabeledTicket, use_judge: bool) -> dict:
    with track_usage() as calls:
        t0 = time.perf_counter()
        try:
            state = GRAPH.invoke({"ticket_id": case.id, "ticket": case.ticket})
            error = None
        except Exception as e:
            state, error = {}, f"{type(e).__name__}: {e}"
        latency = time.perf_counter() - t0

    status = state.get("status")
    action = STATUS_TO_ACTION[status].value if status else "human_review"  # pipeline errors fail to human
    tri = state.get("triage")
    agent = state.get("agent")
    row = {
        "id": case.id, "tags": case.tags, "notes": case.notes,
        "expected_language": expected_language(case.tags), "language": tri.language if tri else None,
        "team": state["routing"].team if "routing" in state else None,
        "subject": case.ticket.subject, "body": case.ticket.body,
        "expected_category": case.expected_category.value, "category": tri.category.value if tri else None,
        "expected_priority": case.expected_priority.value, "priority": tri.priority.value if tri else None,
        "expected_action": case.expected_action.value, "action": action,
        "status_reasons": state.get("status_reasons", []),
        "routing_hits": [h.rule for h in state["routing"].hits] if "routing" in state else [],
        "injection_flagged": bool(tri and tri.injection_suspected),
        "draft": agent.output.draft_reply if agent else None,
        "confidence": agent.output.confidence if agent else None,
        "raw_confidence": agent.raw_confidence if agent else None,
        "sources": agent.output.sources if agent else [],
        "tools": [f"{c.step}:{c.tool}" for c in agent.trace] if agent else [],
        "guardrail_flags": agent.guardrail_flags if agent else [],
        "latency_s": round(latency, 2),
        "input_tokens": sum(c.input_tokens for c in calls),
        "output_tokens": sum(c.output_tokens for c in calls),
        "llm_calls": len(calls),
        "error": error,
        "claims": None,
        "evidence": evidence_from_state(state) if agent else [],
    }
    if use_judge and agent:
        try:
            row["claims"] = [c.model_dump() for c in judge(agent.output.draft_reply, row["evidence"]).claims]
        except Exception as e:
            row["judge_error"] = str(e)
    return row


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def write_report(rows: list[dict], wall_s: float) -> str:
    s = get_settings()
    esc = M.precision_recall(rows)
    auto = M.auto_send(rows)
    g = M.groundedness(rows)
    lat = M.latency(rows)
    conf = M.confusion(rows)
    inj = [r for r in rows if "prompt_injection" in r["tags"]]
    inj_safe = [r for r in inj if r["action"] != "send" and not (r["draft"] and INJECTION_ECHO.search(r["draft"]))]
    pri_close = sum(abs(int(r["priority"][1]) - int(r["expected_priority"][1])) <= 1
                    for r in rows if r["priority"]) / len(rows)

    lines = [
        "# Evaluation report",
        "",
        f"_Run {datetime.now():%Y-%m-%d %H:%M} · {len(rows)} tickets · triage `{s.triage_model}` · "
        f"agent `{s.agent_model}` · judge `{s.judge_model}` · CPU-only · wall time {wall_s / 60:.1f} min_",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Category accuracy | **{pct(M.accuracy(rows, 'category', 'expected_category'))}** |",
        f"| Priority accuracy (exact / within 1 level) | **{pct(M.accuracy(rows, 'priority', 'expected_priority'))}** / {pct(pri_close)} |",
        f"| Final action accuracy (send / review / escalate) | **{pct(M.accuracy(rows, 'action', 'expected_action'))}** |",
        f"| Escalation precision / recall | **{pct(esc['precision'])} / {pct(esc['recall'])}** (TP {esc['tp']}, FP {esc['fp']}, FN {esc['fn']}) |",
        f"| Auto-resolution rate | **{pct(auto['auto_resolution_rate'])}** ({auto['auto_sent']} tickets) |",
        f"| Unsafe auto-sends | **{auto['unsafe_auto_sent']}** {auto['unsafe_ids'] or ''} |",
        f"| Prompt-injection cases handled safely | **{len(inj_safe)}/{len(inj)}** |",
        f"| Groundedness: claims supported (LLM judge) | **{pct(g['claim_support_rate'])}** |",
        f"| Groundedness: fully grounded drafts | **{pct(g['fully_grounded_rate'])}** of {g['judged']} judged |",
        f"| Drafts flagged by deterministic guardrails | {pct(g['guardrail_flag_rate'])} of {g['drafts']} |",
        f"| Latency per ticket (mean / p50 / p95) | {lat.get('mean', 0):.1f}s / {lat.get('p50', 0):.1f}s / {lat.get('p95', 0):.1f}s |",
        f"| Tokens per ticket (mean in / out) | {sum(r['input_tokens'] for r in rows) / len(rows):.0f} / {sum(r['output_tokens'] for r in rows) / len(rows):.0f} |",
        "| Cost per ticket | $0 API cost (local models); compute = latency above |",
        "",
        "## Action confusion matrix (rows = expected, columns = predicted)",
        "",
        "| expected \\ predicted | " + " | ".join(M.ACTIONS) + " |",
        "|---|" + "---|" * len(M.ACTIONS),
    ]
    for a in M.ACTIONS:
        lines.append(f"| **{a}** | " + " | ".join(str(conf[a][b]) for b in M.ACTIONS) + " |")

    lines += ["", "## English vs Arabic", "",
              "| slice | n | language detected | category | priority | action | escalation recall | unsafe auto-sends |",
              "|---|---|---|---|---|---|---|---|"]
    for name, sl in M.language_slices(rows).items():
        if not sl:
            continue
        e, a = M.precision_recall(sl), M.auto_send(sl)
        lines.append(
            f"| {name} | {len(sl)} | {pct(M.accuracy(sl, 'language', 'expected_language'))} | "
            f"{pct(M.accuracy(sl, 'category', 'expected_category'))} | "
            f"{pct(M.accuracy(sl, 'priority', 'expected_priority'))} | "
            f"{pct(M.accuracy(sl, 'action', 'expected_action'))} | "
            f"{pct(e['recall']) if e['tp'] + e['fn'] else 'n/a'} | {a['unsafe_auto_sent']} |")

    lines += ["", "## Action accuracy by tag", "", "| tag | n | accuracy |", "|---|---|---|"]
    for t, v in M.by_tag(rows).items():
        lines.append(f"| {t} | {v['n']} | {pct(v['action_acc'])} |")

    misses = [r for r in rows if r["action"] != r["expected_action"]]
    lines += ["", f"## Misrouted tickets ({len(misses)})", "", "| id | expected | got | why | notes |", "|---|---|---|---|---|"]
    for r in misses:
        why = "; ".join(r["routing_hits"] or r["status_reasons"])[:120].replace("|", "/")
        lines.append(f"| {r['id']} | {r['expected_action']} | {r['action']} | {why} | {r['notes']} |")

    errors = [r for r in rows if r["error"]]
    if errors:
        lines += ["", "## Pipeline errors", ""] + [f"- {r['id']}: {r['error']}" for r in errors]
    return "\n".join(lines) + "\n"


def write_spot_checks(rows: list[dict], n: int = 6) -> str:
    """Human spot-check sheet: the judge needs auditing too."""
    drafted = [r for r in rows if r["draft"]]
    sample = random.Random(7).sample(drafted, min(n, len(drafted)))
    out = ["# Groundedness spot checks", "",
           "For each draft: read the reply, check each judge verdict against the evidence, and mark "
           "whether you agree. Disagreements measure how far to trust the LLM judge.", ""]
    for r in sample:
        out += [f"## {r['id']}: {r['subject']}", "", f"**Customer:** {r['body']}", "",
                "**Reply:**", "", "> " + r["draft"].replace("\n", "\n> "), "", "**Judge verdicts:**", ""]
        for c in r["claims"] or []:
            out.append(f"- [{'✓' if c['supported'] else '✗'}] {c['claim']} _(evidence: {c['evidence_id'] or '—'})_ "
                       "· human agrees? [ ]")
        out += ["", "<details><summary>Evidence</summary>", ""]
        out += [f"- **{e['id']}**: {e['text'][:400]}" for e in r["evidence"]]
        out += ["", "</details>", ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--out", help="report folder (default evals/reports); use one per run to keep a baseline")
    args = ap.parse_args()

    cases = [LabeledTicket.model_validate(x) for x in json.loads((DATA_DIR / "eval_set.json").read_text("utf-8"))]
    if args.ids:
        cases = [c for c in cases if c.id in set(args.ids)]

    global REPORTS
    if args.out:
        REPORTS = Path(args.out)
    REPORTS.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.perf_counter()
    for i, case in enumerate(cases, 1):
        row = run_case(case, use_judge=not args.no_judge)
        rows.append(row)
        mark = "ok " if row["action"] == row["expected_action"] else "MISS"
        print(f"[{i:>2}/{len(cases)}] {case.id} {mark} {row['action']:<12} (exp {row['expected_action']:<12}) "
              f"{row['latency_s']:>6.1f}s", flush=True)
        (REPORTS / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), "utf-8")

    report = write_report(rows, time.perf_counter() - t0)
    (REPORTS / "eval_report.md").write_text(report, "utf-8")
    (REPORTS / "spot_checks.md").write_text(write_spot_checks(rows), "utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()
