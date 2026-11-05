"""Pure metric functions over per-case result dicts (no LLM, unit-testable)."""
from collections import Counter, defaultdict
from statistics import mean, median

ACTIONS = ["send", "human_review", "escalate"]


def accuracy(rows, got, exp) -> float:
    return sum(r[got] == r[exp] for r in rows) / len(rows) if rows else 0.0


def precision_recall(rows, positive="escalate") -> dict:
    tp = sum(r["action"] == positive and r["expected_action"] == positive for r in rows)
    fp = sum(r["action"] == positive and r["expected_action"] != positive for r in rows)
    fn = sum(r["action"] != positive and r["expected_action"] == positive for r in rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    rcl = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": p, "recall": rcl, "f1": 2 * p * rcl / (p + rcl) if p + rcl else 0.0,
            "tp": tp, "fp": fp, "fn": fn}


def confusion(rows) -> dict[str, Counter]:
    m = {a: Counter() for a in ACTIONS}
    for r in rows:
        m[r["expected_action"]][r["action"]] += 1
    return m


def auto_send(rows) -> dict:
    sent = [r for r in rows if r["action"] == "send"]
    unsafe = [r for r in sent if r["expected_action"] != "send"]
    return {"auto_resolution_rate": len(sent) / len(rows) if rows else 0.0,
            "auto_sent": len(sent), "unsafe_auto_sent": len(unsafe),
            "unsafe_rate": len(unsafe) / len(sent) if sent else 0.0,
            "unsafe_ids": [r["id"] for r in unsafe]}


def by_tag(rows) -> dict[str, dict]:
    groups = defaultdict(list)
    for r in rows:
        for t in r["tags"]:
            groups[t].append(r)
    return {t: {"n": len(g), "action_acc": accuracy(g, "action", "expected_action")}
            for t, g in sorted(groups.items())}


def language_slices(rows) -> dict[str, list]:
    return {
        "English": [r for r in rows if r["expected_language"] == "en"],
        "Arabic (script, incl. mixed)": [r for r in rows if r["expected_language"] in ("ar", "mixed")],
        "Arabizi": [r for r in rows if r["expected_language"] == "ar_latn"],
    }


def latency(rows) -> dict:
    xs = sorted(r["latency_s"] for r in rows)
    if not xs:
        return {}
    return {"mean": mean(xs), "p50": median(xs), "p95": xs[min(len(xs) - 1, int(0.95 * len(xs)))], "max": xs[-1]}


def groundedness(rows) -> dict:
    judged = [r for r in rows if r.get("claims") is not None]
    claims = [c for r in judged for c in r["claims"]]
    fully = [r for r in judged if all(c["supported"] for c in r["claims"])]
    flagged = [r for r in rows if r.get("guardrail_flags")]
    drafted = [r for r in rows if r.get("draft")]
    return {
        "drafts": len(drafted),
        "judged": len(judged),
        "claim_support_rate": sum(c["supported"] for c in claims) / len(claims) if claims else 0.0,
        "fully_grounded_rate": len(fully) / len(judged) if judged else 0.0,
        "guardrail_flag_rate": len(flagged) / len(drafted) if drafted else 0.0,
    }
