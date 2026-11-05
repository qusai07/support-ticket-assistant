"""Runtime settings: env defaults (app/config.py) overridden by admin edits in the DB.

The API and the worker are separate processes, so the DB is the shared source of
truth. Values are cached for a few seconds: an admin change reaches the worker
within CACHE_TTL_S, without a restart.
"""
import time
from typing import Any

from app.config import get_settings

CACHE_TTL_S = 10

# key -> (type, validator description). Only these keys are editable.
EDITABLE: dict[str, dict[str, Any]] = {
    "refund_escalation_threshold": {"type": "number", "min": 0, "max": 100000},
    "auto_send_confidence": {"type": "number", "min": 0.5, "max": 1.0},
    "very_negative_sentiment": {"type": "number", "min": -1.0, "max": 0.0},
    "low_risk_categories": {"type": "categories"},
    "auto_send_enabled": {"type": "bool"},
    "triage_model": {"type": "string"},
    "agent_model": {"type": "string"},
    "team_routing": {"type": "routing"},
    "sla_hours": {"type": "sla"},
}

DEFAULT_SLA_HOURS = {"P1": 1.0, "P2": 4.0, "P3": 24.0, "P4": 72.0}
SLA_AT_RISK_FRACTION = 0.75  # "at risk" once 75% of the target time has elapsed

# Which team owns a ticket. The ORDER (most severe first) is fixed in code: a safety issue
# always outranks a VIP flag. Admins edit only WHICH team each key maps to.
SIGNAL_ORDER = ["safety", "legal", "fraud", "chargeback"]
RULE_ORDER = ["vip_customer", "very_negative_sentiment", "refund_over_threshold"]
CATEGORY_KEYS = ["billing", "refund", "shipping", "technical", "account", "other"]
DEFAULT_TEAM_ROUTING = {
    "signals": {"safety": "Product Safety", "legal": "Legal & Compliance", "fraud": "Account Security",
                "chargeback": "Billing Disputes"},
    "rules": {"vip_customer": "VIP Care", "very_negative_sentiment": "Customer Care (Senior)",
              "refund_over_threshold": "Returns & Refunds"},
    "categories": {"billing": "Billing", "refund": "Returns & Refunds", "shipping": "Logistics",
                   "technical": "Technical Support", "account": "Accounts", "other": "Customer Care"},
}

_cache: dict[str, Any] = {}
_cache_at = 0.0


def defaults() -> dict[str, Any]:
    s = get_settings()
    return {
        "refund_escalation_threshold": s.refund_escalation_threshold,
        "auto_send_confidence": s.auto_send_confidence,
        "very_negative_sentiment": s.very_negative_sentiment,
        "low_risk_categories": list(s.low_risk_categories),
        "auto_send_enabled": True,  # kill switch: off = every draft goes to human review
        "triage_model": s.triage_model,
        "agent_model": s.agent_model,
        "team_routing": DEFAULT_TEAM_ROUTING,
        "sla_hours": DEFAULT_SLA_HOURS,
    }


def get_runtime(force: bool = False) -> dict[str, Any]:
    global _cache, _cache_at
    if not force and _cache and time.monotonic() - _cache_at < CACHE_TTL_S:
        return _cache
    values = defaults()
    try:
        from sqlmodel import Session, select

        from app.db.session import engine
        from app.models import db
        with Session(engine) as s:
            for row in s.exec(select(db.AppSetting)).all():
                if row.key in EDITABLE:
                    values[row.key] = row.value.get("v")
    except Exception:
        pass  # no DB / table yet (unit tests, first boot): env defaults apply
    _cache, _cache_at = values, time.monotonic()
    return values


def validate(key: str, value: Any) -> Any:
    from app.models.enums import Category
    spec = EDITABLE.get(key)
    if spec is None:
        raise ValueError(f"'{key}' is not an editable setting")
    t = spec["type"]
    if t == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{key} must be a number")
        if not spec["min"] <= value <= spec["max"]:
            raise ValueError(f"{key} must be between {spec['min']} and {spec['max']}")
        return float(value)
    if t == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false")
        return value
    if t == "categories":
        valid = {c.value for c in Category}
        if not isinstance(value, list) or not set(value) <= valid:
            raise ValueError(f"{key} must be a list of: {sorted(valid)}")
        if "refund" in value or "billing" in value:
            raise ValueError("refund and billing can't be low-risk: money decisions always get human review")
        return value
    if t == "sla":
        if not isinstance(value, dict):
            raise ValueError("sla_hours must be an object like {'P1': 1, 'P2': 4, ...}")
        clean = {}
        for p in ("P1", "P2", "P3", "P4"):
            v = value.get(p, DEFAULT_SLA_HOURS[p])
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.25 <= v <= 720:
                raise ValueError(f"sla_hours.{p} must be between 0.25 and 720 hours")
            clean[p] = float(v)
        if not clean["P1"] <= clean["P2"] <= clean["P3"] <= clean["P4"]:
            raise ValueError("SLA targets must not decrease from P1 to P4")
        return clean
    if t == "routing":
        from app.auth.permissions import team_names
        teams = set(team_names())
        if not isinstance(value, dict):
            raise ValueError("team_routing must be an object")
        clean = {}
        for section, keys in (("signals", SIGNAL_ORDER), ("rules", RULE_ORDER), ("categories", CATEGORY_KEYS)):
            sec = value.get(section, {})
            clean[section] = {}
            for k in keys:
                team = sec.get(k, DEFAULT_TEAM_ROUTING[section][k])
                if team not in teams:
                    raise ValueError(f"team_routing.{section}.{k}: unknown or inactive team '{team}'")
                clean[section][k] = team
        return clean
    if t == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        return value.strip()
    raise ValueError("unsupported type")
