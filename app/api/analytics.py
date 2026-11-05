"""Analytics: latest offline eval results + operational metrics over time."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth.deps import require
from app.auth.permissions import Permission
from app.db.session import get_session
from app.models import db

router = APIRouter(prefix="/analytics", tags=["analytics"])
RESULTS = Path(__file__).resolve().parents[2] / "evals" / "reports" / "results.json"


@router.get("/eval")
def eval_summary(_: db.User = Depends(require(Permission.ANALYTICS_VIEW))):
    if not RESULTS.exists():
        return {"available": False}
    from evals import metrics as M
    rows = json.loads(RESULTS.read_text("utf-8"))
    if not rows:
        return {"available": False}
    rows = [r for r in rows if r.get("expected_language")] or rows
    for r in rows:
        r.setdefault("expected_language", "en")
    esc, auto, g = M.precision_recall(rows), M.auto_send(rows), M.groundedness(rows)
    conf = M.confusion(rows)
    slices = {}
    for name, sl in M.language_slices(rows).items():
        if sl:
            slices[name] = {"n": len(sl), "category": M.accuracy(sl, "category", "expected_category"),
                            "priority": M.accuracy(sl, "priority", "expected_priority"),
                            "action": M.accuracy(sl, "action", "expected_action")}
    return {
        "available": True, "n": len(rows), "modified": RESULTS.stat().st_mtime,
        "category_acc": M.accuracy(rows, "category", "expected_category"),
        "priority_acc": M.accuracy(rows, "priority", "expected_priority"),
        "action_acc": M.accuracy(rows, "action", "expected_action"),
        "escalation": esc, "auto_send": auto, "groundedness": g, "latency": M.latency(rows),
        "confusion": {k: dict(v) for k, v in conf.items()}, "by_language": slices,
        "by_tag": M.by_tag(rows),
    }


@router.get("/ops")
def ops(days: int = 14, _: db.User = Depends(require(Permission.ANALYTICS_VIEW)),
        session: Session = Depends(get_session)):
    """Daily ticket volume and outcomes, review decisions, edit rate, latency."""
    tickets = session.exec(select(db.Ticket)).all()
    runs = {r.ticket_id: r for r in session.exec(select(db.PipelineRun)).all()}
    reviews = session.exec(select(db.Review)).all()
    daily: dict[str, Counter] = defaultdict(Counter)
    for t in tickets:
        daily[t.created_at.date().isoformat()][t.status.value] += 1
    days_sorted = sorted(daily)[-days:]
    lat = [r.total_latency_ms / 1000 for r in runs.values()]
    decisions = Counter(r.decision for r in reviews)
    reviewed = sum(decisions.values())
    return {
        "daily": [{"date": d, **daily[d]} for d in days_sorted],
        "by_team": Counter(t.team or "unrouted" for t in tickets),
        "by_language": Counter(t.language or "unknown" for t in tickets),
        "by_priority": Counter(t.priority or "unknown" for t in tickets),
        "reviews": decisions,
        "edit_rate": decisions.get("edit", 0) / reviewed if reviewed else None,
        "avg_latency_s": sum(lat) / len(lat) if lat else None,
        "auto_resolved": sum(1 for t in tickets if t.status.value == "ready_to_send"),
        "total": len(tickets),
    }
