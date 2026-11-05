"""Generate the synthetic dataset. Deterministic (seeded), no LLM needed.

    python -m data.generate

Output files are committed to the repo, so anyone can run the project without
regenerating. Every record is validated against the Pydantic schemas in
app/models/schemas.py before it is written; a bad record fails loudly here
instead of confusing the agent later.
"""
import json
import random
import zlib
from datetime import date, timedelta
from pathlib import Path

from app.models.schemas import (
    Customer,
    HistoricalTicket,
    KBArticle,
    LabeledTicket,
    Order,
)
from data.seed_content import (
    CARRIERS,
    EVAL_TICKETS,
    FIXTURE_CUSTOMERS,
    FIXTURE_ORDERS,
    HISTORY_TEMPLATES,
    KB_ARTICLES,
    PRODUCTS,
)
from data.seed_content_ar import EVAL_TICKETS_AR, KB_AR

SEED = 42
OUT = Path(__file__).parent
REF = date(2026, 11, 1)
N_CUSTOMERS, N_ORDERS, N_HISTORY = 50, 150, 200

FIRST = ["Adam", "Leila", "Noah", "Hana", "Yusuf", "Emma", "Karim", "Zoe", "Ali", "Mia", "Samir", "Chloe",
         "Tariq", "Ava", "Hassan", "Isla", "Fadi", "Grace", "Ziad", "Ella", "Rami", "Lily", "Bilal", "Nora",
         "Jad", "Sofia", "Amir", "Ruby", "Khaled", "Ivy", "Majd", "Alice", "Tamer", "Julia", "Wael", "Clara",
         "Hadi", "Eva", "Fares", "Lea"]
LAST = ["Nasser", "Smith", "Haddad", "Garcia", "Mansour", "Kim", "Ibrahim", "Rossi", "Darwish", "Novak",
        "Aziz", "Tanaka", "Sabbagh", "Silva", "Hamdan", "Weber", "Jaber", "Dubois", "Khoury", "Lund"]

PRICE = {p["sku"]: p for p in PRODUCTS}


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


# ---------------------------------------------------------------- customers
def build_customers(rng: random.Random) -> list[dict]:
    customers = [dict(c) for c in FIXTURE_CUSTOMERS]
    used = {c["email"] for c in customers}
    while len(customers) < N_CUSTOMERS:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first}.{last}@example.{rng.choice(['com', 'org', 'net'])}".lower()
        if email in used:
            continue
        used.add(email)
        plan = rng.choices(["free", "pro", "enterprise"], weights=[60, 32, 8])[0]
        renewed = iso(REF - timedelta(days=rng.randint(1, 360))) if plan != "free" else None
        customers.append(dict(
            id=f"CUST-{len(customers) + 1:03d}", name=f"{first} {last}", email=email, plan=plan,
            tenure_months=rng.randint(1, 72), is_vip=(plan == "enterprise" and rng.random() < 0.5),
            plan_renewed_at=renewed,
        ))
    return customers


# ---------------------------------------------------------------- orders
def _materialize(spec: dict) -> dict:
    """Turn a compact order spec into a full Order record."""
    items = [dict(sku=s, name=PRICE[s]["name"], qty=1, unit_price=PRICE[s]["price"]) for s in spec["skus"]]
    total = round(sum(i["unit_price"] * i["qty"] for i in items), 2)
    shipped = spec["status"] not in ("processing", "cancelled")
    carrier = spec.get("carrier")
    return dict(
        id=spec["id"], customer_id=spec["customer_id"], status=spec["status"], items=items, total=total,
        payment=dict(method=spec.get("method", "card"), status=spec["pay_status"],
                     charged_count=spec["charged_count"], amount=round(total * spec["charged_count"], 2)),
        tracking=dict(carrier=carrier if shipped else None,
                      number=f"{carrier[:2].upper()}{zlib.crc32(spec['id'].encode()):010d}" if shipped and carrier else None,
                      eta=spec.get("eta")),
        created_at=spec["created_at"], delivered_at=spec.get("delivered_at"),
    )


def build_orders(rng: random.Random, customers: list[dict]) -> list[dict]:
    orders = [_materialize(o) for o in FIXTURE_ORDERS]
    regular_skus = [p["sku"] for p in PRODUCTS]
    n = len(orders)
    while len(orders) < N_ORDERS:
        n += 1
        created = REF - timedelta(days=rng.randint(1, 200))
        eta = created + timedelta(days=rng.randint(3, 7))
        if eta < REF - timedelta(days=2):
            status = rng.choices(["delivered", "returned", "cancelled"], weights=[88, 7, 5])[0]
        elif created > REF - timedelta(days=2):
            status = "processing"
        else:
            status = rng.choice(["shipped", "in_transit"])
        skus = rng.sample(regular_skus, k=rng.choices([1, 2, 3], weights=[70, 25, 5])[0])
        pay = {"returned": "refunded", "cancelled": "refunded"}.get(status, "paid")
        orders.append(_materialize(dict(
            id=f"ORD-{10000 + n}", customer_id=rng.choice(customers)["id"], status=status, skus=skus,
            created_at=iso(created), eta=iso(eta) if status != "cancelled" else None,
            delivered_at=iso(eta) if status in ("delivered", "returned") else None,
            pay_status=pay, charged_count=1, carrier=rng.choice(CARRIERS),
            method=rng.choices(["card", "paypal", "bank_transfer"], weights=[70, 25, 5])[0],
        )))
    return orders


# ---------------------------------------------------------------- historical tickets
def build_history(rng: random.Random, customers: list[dict], orders: list[dict]) -> list[dict]:
    by_customer: dict[str, list[dict]] = {}
    for o in orders:
        by_customer.setdefault(o["customer_id"], []).append(o)
    eligible = [c for c in customers if c["id"] in by_customer]

    history = []
    for i in range(N_HISTORY):
        cat, pri, subj, body, resolution, refs = HISTORY_TEMPLATES[i % len(HISTORY_TEMPLATES)]
        cust = rng.choice(eligible)
        order = rng.choice(by_customer[cust["id"]])
        fill = dict(order=order["id"], product=order["items"][0]["name"], name=cust["name"].split()[0])
        history.append(dict(
            id=f"T-{i + 1:04d}", subject=subj.format(**fill), body=body.format(**fill), category=cat,
            priority=pri, customer_email=cust["email"], resolution=resolution, kb_refs=refs,
        ))
        cust.setdefault("past_ticket_ids", []).append(f"T-{i + 1:04d}")
    return history


# ---------------------------------------------------------------- eval set
def build_eval(rng: random.Random) -> list[dict]:
    out = []
    for i, t in enumerate(EVAL_TICKETS + EVAL_TICKETS_AR):
        created = f"{REF.isoformat()}T{8 + i % 10:02d}:{rng.randint(0, 59):02d}:00"
        out.append(dict(
            id=t["id"],
            ticket=dict(subject=t["subject"], body=t["body"], customer_email=t["email"],
                        channel=t["channel"], created_at=created),
            expected_category=t["cat"], expected_priority=t["pri"], expected_action=t["action"],
            tags=t["tags"], notes=t["notes"],
        ))
    return out


# ---------------------------------------------------------------- main
def _write(name: str, rows: list[dict], model) -> None:
    validated = [model.model_validate(r).model_dump(mode="json") for r in rows]
    (OUT / name).write_text(json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {name:<26} {len(validated):>4} records")


def main() -> None:
    rng = random.Random(SEED)
    customers = build_customers(rng)
    orders = build_orders(rng, customers)
    for c in customers:
        c["order_ids"] = [o["id"] for o in orders if o["customer_id"] == c["id"]]
    history = build_history(rng, customers, orders)
    eval_set = build_eval(rng)

    print("Writing dataset:")
    missing = [a["id"] for a in KB_ARTICLES if a["id"] not in KB_AR]
    assert not missing, f"KB articles missing an Arabic version: {missing}"
    kb = [{**a, "title_ar": KB_AR[a["id"]][0], "body_ar": KB_AR[a["id"]][1]} for a in KB_ARTICLES]
    _write("kb_articles.json", kb, KBArticle)
    _write("customers.json", customers, Customer)
    _write("orders.json", orders, Order)
    _write("historical_tickets.json", history, HistoricalTicket)
    _write("eval_set.json", eval_set, LabeledTicket)


if __name__ == "__main__":
    main()
