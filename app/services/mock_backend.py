"""Mock CRM + order system + refund policy engine, backed by data/*.json.

check_refund_eligibility is the refund policy (KB-006/007/009/010/015) written as
code. The LLM never decides eligibility; it only explains this function's answer.
"""
import json
from datetime import date
from functools import lru_cache

from app.config import DATA_DIR, get_settings
from app.models.schemas import Customer, HistoricalTicket, Order

RETURN_WINDOW_DAYS = 30
FINAL_SALE_DOA_DAYS = 7
RETURN_LABEL_FEE = 6.95


@lru_cache
def _customers() -> dict[str, Customer]:
    rows = json.loads((DATA_DIR / "customers.json").read_text("utf-8"))
    return {r["email"].lower(): Customer.model_validate(r) for r in rows}


@lru_cache
def _orders() -> dict[str, Order]:
    rows = json.loads((DATA_DIR / "orders.json").read_text("utf-8"))
    return {r["id"]: Order.model_validate(r) for r in rows}


@lru_cache
def _history() -> dict[str, HistoricalTicket]:
    rows = json.loads((DATA_DIR / "historical_tickets.json").read_text("utf-8"))
    return {r["id"]: HistoricalTicket.model_validate(r) for r in rows}


def today() -> date:
    return date.fromisoformat(get_settings().reference_date)


def find_customer(email: str) -> Customer | None:
    return _customers().get(email.lower().strip())


def find_order(order_id: str) -> Order | None:
    return _orders().get(order_id.upper().strip())


def customer_summary(c: Customer) -> dict:
    past = [_history()[t] for t in c.past_ticket_ids[-5:] if t in _history()]
    return {
        "customer_id": c.id, "name": c.name, "plan": c.plan.value, "tenure_months": c.tenure_months,
        "is_vip": c.is_vip, "plan_renewed_at": c.plan_renewed_at, "order_ids": c.order_ids,
        "recent_tickets": [{"id": t.id, "subject": t.subject, "category": t.category.value} for t in past],
    }


def check_refund_eligibility(order: Order) -> dict:
    base = {"order_id": order.id, "order_total": order.total, "order_status": order.status.value,
            "payment_status": order.payment.status}
    status = order.status.value

    if status == "processing":
        return {**base, "eligible": True, "type": "cancellation", "refundable_amount": order.total,
                "reason": "Order has not shipped and can be cancelled for a full refund.", "kb_refs": ["KB-009"]}
    if status in ("cancelled", "returned"):
        return {**base, "eligible": False, "type": "none", "refundable_amount": 0.0,
                "reason": f"Order is already {status}; refund was already processed.", "kb_refs": ["KB-008"]}
    if status in ("shipped", "in_transit"):
        return {**base, "eligible": False, "type": "none", "refundable_amount": 0.0,
                "reason": "Order has shipped and cannot be cancelled. It can be returned within 30 days after delivery.",
                "kb_refs": ["KB-009", "KB-006"]}
    if status == "lost":
        return {**base, "eligible": True, "type": "lost_package", "refundable_amount": order.total,
                "reason": "Package marked lost by carrier. Customer may choose a free reshipment or a full refund.",
                "kb_refs": ["KB-015"]}

    # delivered
    days = (today() - date.fromisoformat(order.delivered_at)).days if order.delivered_at else None
    final_sale = [i for i in order.items if i.sku.startswith("FS-")]
    regular = [i for i in order.items if not i.sku.startswith("FS-")]
    regular_amount = round(sum(i.unit_price * i.qty for i in regular), 2)
    result = {**base, "days_since_delivery": days, "return_window_days": RETURN_WINDOW_DAYS,
              "final_sale_items": [i.name for i in final_sale]}

    if days is None or days > RETURN_WINDOW_DAYS:
        return {**result, "eligible": False, "type": "none", "refundable_amount": 0.0,
                "reason": f"Delivered {days} days ago; outside the {RETURN_WINDOW_DAYS}-day return window.",
                "kb_refs": ["KB-006"]}
    if not regular:
        doa_ok = days <= FINAL_SALE_DOA_DAYS
        return {**result, "eligible": False, "type": "none", "refundable_amount": 0.0,
                "replacement_if_dead_on_arrival": doa_ok,
                "reason": "All items are final sale and cannot be refunded."
                          + (" If dead on arrival, a same-item replacement is available." if doa_ok else ""),
                "kb_refs": ["KB-007"]}
    if order.payment.status == "partially_refunded":
        result["note"] = "This order already received a partial refund."
    return {**result, "eligible": True, "type": "return", "refundable_amount": regular_amount,
            "return_label_fee_change_of_mind": RETURN_LABEL_FEE, "defective_items_return_free": True,
            "reason": f"Delivered {days} days ago, within the {RETURN_WINDOW_DAYS}-day window."
                      + (" Final sale items excluded." if final_sale else ""),
            "kb_refs": ["KB-006", "KB-010"] + (["KB-007"] if final_sale else [])}
