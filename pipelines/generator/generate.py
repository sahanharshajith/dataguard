"""
Deterministic sample-data generator for the e-commerce demo.

python -m pipelines.generator --scenario dirty --as-of 2026-11-18 --out data/landing

The same scenario, date and seed always produce identical files. Every batch also gets a
`batch.json` manifest that records the ground truth: what was planted and how many rows exist.
"""

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import StrEnum
from pathlib import Path

N_CUSTOMERS = 1000
N_PRODUCTS = 100
DEFAULT_ORDERS = 5000

COLUMNS = {
    "customers": ["customer_id", "first_name", "last_name", "email", "country", "signup_date"],
    "products": ["product_id", "product_name", "category", "unit_price"],
    "orders": ["order_id", "customer_id", "order_date", "status", "order_total"],
    "order_items": ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "line_total"],
    "payments": ["payment_id", "order_id", "payment_method", "amount", "paid_at", "payment_status"],
}

# What the `dirty` scenario plants in `orders`. Every group touches different orders,
# so each count below is exact.
PLANTED_PROBLEMS = {
    "duplicate_order_ids": 25,   # an order row appears twice
    "missing_customer_ids": 40,  # customer_id is empty
    "invalid_totals": 30,        # order_total is 0.00 or negative
    "total_mismatches": 20,      # order_total differs from the sum of its items
    "orphan_customers": 35,      # customer_id points at a customer that does not exist
    "unparseable_totals": 15,    # order_total is the text "N/A"
    "unparseable_dates": 15,     # order_date is the text "yesterday"
}

# Valid data in an untidy shape. Present in EVERY scenario; STAGING is expected to tidy it.
FORMAT_NOISE = {
    "uppercase_emails": 50,
    "lowercase_countries": 50,
    "padded_last_names": 30,
}

FIRST_NAMES = ["Amara", "Nimal", "Kasun", "Sanduni", "Priya", "Arjun", "Maya", "Liam",
               "Emma", "Noah", "Olivia", "Ravi", "Anika", "Chen", "Sofia", "Lucas"]
LAST_NAMES = ["Perera", "Fernando", "Silva", "Wickrama", "Patel", "Singh",
              "Smith", "Johnson", "Garcia", "Kim", "Nguyen", "Brown"]
COUNTRIES = ["LK", "IN", "US", "GB", "DE", "AU", "CA", "SG"]
CATEGORIES = ["electronics", "home", "fashion", "sports", "books", "toys"]
ADJECTIVES = ["Compact", "Deluxe", "Classic", "Smart", "Eco", "Premium", "Basic", "Portable"]
NOUNS = ["Lamp", "Backpack", "Headphones", "Kettle", "Notebook",
         "Sneakers", "Blender", "Speaker", "Watch", "Bottle"]
ORDER_STATUSES = ["placed", "shipped", "delivered", "cancelled"]
ORDER_STATUS_WEIGHTS = [10, 20, 62, 8]
PAYMENT_METHODS = ["card", "paypal", "bank_transfer"]


class Scenario(StrEnum):
    CLEAN = "clean"
    DIRTY = "dirty"
    SCHEMA_DRIFT = "schema_drift"
    VOLUME_DROP = "volume_drop"
    LATE = "late"


@dataclass(frozen=True)
class ScenarioSpec:
    orders: int = DEFAULT_ORDERS
    dirty: bool = False
    extra_orders_column: bool = False
    late_by_days: int = 0


SPECS = {
    Scenario.CLEAN: ScenarioSpec(),
    Scenario.DIRTY: ScenarioSpec(dirty=True),
    Scenario.SCHEMA_DRIFT: ScenarioSpec(extra_orders_column=True),
    Scenario.VOLUME_DROP: ScenarioSpec(orders=600),
    Scenario.LATE: ScenarioSpec(late_by_days=3),
}


def money(cents: int) -> str:
    """Format integer cents as text without touching floating point: 12345 -> '123.45'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def _build_customers(rng: random.Random, as_of: date) -> list[dict]:
    rows = []
    for customer_id in range(1, N_CUSTOMERS + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        rows.append({
            "customer_id": str(customer_id),
            "first_name": first,
            "last_name": last,
            "email": f"{first}.{last}{customer_id}@example.com".lower(),
            "country": rng.choice(COUNTRIES),
            "signup_date": (as_of - timedelta(days=rng.randint(30, 730))).isoformat(),
        })
    for i in rng.sample(range(len(rows)), FORMAT_NOISE["uppercase_emails"]):
        rows[i]["email"] = rows[i]["email"].upper()
    for i in rng.sample(range(len(rows)), FORMAT_NOISE["lowercase_countries"]):
        rows[i]["country"] = rows[i]["country"].lower()
    for i in rng.sample(range(len(rows)), FORMAT_NOISE["padded_last_names"]):
        rows[i]["last_name"] = f" {rows[i]['last_name']} "
    return rows


def _build_products(rng: random.Random) -> tuple[list[dict], list[int]]:
    rows, prices = [], []
    for product_id in range(1, N_PRODUCTS + 1):
        price_cents = rng.randint(500, 20000)
        prices.append(price_cents)
        rows.append({
            "product_id": str(product_id),
            "product_name": f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)}",
            "category": rng.choice(CATEGORIES),
            "unit_price": money(price_cents),
        })
    return rows, prices


def _build_sales(rng: random.Random, as_of: date, n_orders: int, prices: list[int]):
    orders, items, payments = [], [], []
    item_id = 0
    for order_id in range(1, n_orders + 1):
        order_date = as_of - timedelta(days=rng.randint(0, 29))
        status = rng.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        total_cents = 0
        for _ in range(rng.randint(1, 4)):
            item_id += 1
            product_id = rng.randint(1, N_PRODUCTS)
            quantity = rng.randint(1, 5)
            line_cents = quantity * prices[product_id - 1]
            total_cents += line_cents
            items.append({
                "order_item_id": str(item_id),
                "order_id": str(order_id),
                "product_id": str(product_id),
                "quantity": str(quantity),
                "unit_price": money(prices[product_id - 1]),
                "line_total": money(line_cents),
            })
        orders.append({
            "order_id": str(order_id),
            "customer_id": str(rng.randint(1, N_CUSTOMERS)),
            "order_date": order_date.isoformat(),
            "status": status,
            "order_total": money(total_cents),
        })
        if status == "cancelled":
            payment_status = "refunded"
        else:
            payment_status = "failed" if rng.random() < 0.03 else "paid"
        paid_at = datetime.combine(order_date, time(rng.randint(0, 23), rng.randint(0, 59)))
        payments.append({
            "payment_id": str(order_id),
            "order_id": str(order_id),
            "payment_method": rng.choice(PAYMENT_METHODS),
            "amount": money(total_cents),
            "paid_at": f"{paid_at:%Y-%m-%d %H:%M:%S}",
            "payment_status": payment_status,
        })
    return orders, items, payments


def _plant_problems(rng: random.Random, orders: list[dict]) -> dict[str, int]:
    """Damage `orders` in place, touching a different set of orders for each problem."""
    picks = rng.sample(range(len(orders)), sum(PLANTED_PROBLEMS.values()))
    cursor = 0

    def take(problem: str) -> list[int]:
        nonlocal cursor
        chunk = picks[cursor:cursor + PLANTED_PROBLEMS[problem]]
        cursor += PLANTED_PROBLEMS[problem]
        return chunk

    duplicated = take("duplicate_order_ids")
    for i in take("missing_customer_ids"):
        orders[i]["customer_id"] = ""
    for position, i in enumerate(take("invalid_totals")):
        total = orders[i]["order_total"]
        orders[i]["order_total"] = "0.00" if position % 2 == 0 else f"-{total}"
    for i in take("total_mismatches"):
        cents = int(orders[i]["order_total"].replace(".", ""))
        orders[i]["order_total"] = money(cents + 1000)
    for i in take("orphan_customers"):
        orders[i]["customer_id"] = str(900_000 + rng.randint(1, 99_999))
    for i in take("unparseable_totals"):
        orders[i]["order_total"] = "N/A"
    for i in take("unparseable_dates"):
        orders[i]["order_date"] = "yesterday"
    # Exact copies of untouched orders, appended at the end of the file.
    orders.extend(dict(orders[i]) for i in duplicated)
    return dict(PLANTED_PROBLEMS)


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_batch(scenario: Scenario, out_root: Path, as_of: date, seed: int = 42) -> Path:
    """Write one batch of CSV files plus `batch.json`; return the batch directory."""
    spec = SPECS[scenario]
    base_rng = random.Random(f"{seed}:{as_of.isoformat()}")
    problem_rng = random.Random(f"{seed}:{as_of.isoformat()}:{scenario.value}")

    products, prices = _build_products(base_rng)
    orders, items, payments = _build_sales(base_rng, as_of, spec.orders, prices)
    tables = {
        "customers": _build_customers(base_rng, as_of),
        "products": products,
        "orders": orders,
        "order_items": items,
        "payments": payments,
    }
    columns = {name: list(cols) for name, cols in COLUMNS.items()}

    planted: dict[str, int] = {}
    if spec.dirty:
        planted = _plant_problems(problem_rng, orders)
    if spec.extra_orders_column:
        columns["orders"].append("coupon_code")
        for row in orders:
            row["coupon_code"] = problem_rng.choice(["SAVE10", "FREESHIP", ""])

    batch_id = f"{as_of.isoformat()}_{scenario.value}"
    batch_dir = Path(out_root) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        _write_csv(batch_dir / f"{name}.csv", columns[name], rows)

    # None means "use the real time of ingestion"; only the late scenario fixes a past time.
    loaded_at = None
    if spec.late_by_days:
        arrival = datetime.combine(as_of, time(2, 0), tzinfo=timezone.utc)
        loaded_at = (arrival - timedelta(days=spec.late_by_days)).isoformat()

    manifest = {
        "batch_id": batch_id,
        "scenario": scenario.value,
        "as_of": as_of.isoformat(),
        "seed": seed,
        "loaded_at": loaded_at,
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "planted_problems": planted,
        "format_noise": dict(FORMAT_NOISE),
    }
    (batch_dir / "batch.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return batch_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate one batch of e-commerce sample data.")
    parser.add_argument("--scenario", choices=[s.value for s in Scenario], default="clean")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="batch date, YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--out", type=Path, default=Path("data/landing"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    as_of = args.as_of or datetime.now(timezone.utc).date()
    batch_dir = generate_batch(Scenario(args.scenario), args.out, as_of, args.seed)
    print(f"Wrote {batch_dir}")