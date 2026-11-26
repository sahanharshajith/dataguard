import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation

import pytest

from pipelines.generator.generate import (
    COLUMNS,
    FORMAT_NOISE,
    N_CUSTOMERS,
    PLANTED_PROBLEMS,
    Scenario,
    generate_batch,
)

AS_OF = date(2026, 11, 16)


def read(batch_dir, table):
    with (batch_dir / f"{table}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def manifest(batch_dir):
    return json.loads((batch_dir / "batch.json").read_text(encoding="utf-8"))


def number(text):
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def items_total_by_order(batch_dir):
    totals = {}
    for item in read(batch_dir, "order_items"):
        totals[item["order_id"]] = totals.get(item["order_id"], Decimal(0)) + Decimal(item["line_total"])
    return totals


def test_same_inputs_give_identical_files(tmp_path):
    first = generate_batch(Scenario.DIRTY, tmp_path / "a", AS_OF, seed=1)
    second = generate_batch(Scenario.DIRTY, tmp_path / "b", AS_OF, seed=1)
    for name in [f"{table}.csv" for table in COLUMNS] + ["batch.json"]:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_a_different_seed_gives_different_data(tmp_path):
    first = generate_batch(Scenario.CLEAN, tmp_path / "a", AS_OF, seed=1)
    second = generate_batch(Scenario.CLEAN, tmp_path / "b", AS_OF, seed=2)
    assert (first / "orders.csv").read_bytes() != (second / "orders.csv").read_bytes()


def test_clean_batch_has_the_expected_sizes(batches):
    counts = manifest(batches[Scenario.CLEAN])["row_counts"]
    assert counts["customers"] == 1000
    assert counts["products"] == 100
    assert counts["orders"] == 5000
    assert counts["payments"] == 5000
    assert 5000 <= counts["order_items"] <= 20000


def test_clean_order_totals_equal_the_sum_of_their_items(batches):
    batch = batches[Scenario.CLEAN]
    sums = items_total_by_order(batch)
    for order in read(batch, "orders"):
        assert Decimal(order["order_total"]) == sums[order["order_id"]]


def test_clean_foreign_keys_all_resolve(batches):
    batch = batches[Scenario.CLEAN]
    customer_ids = {row["customer_id"] for row in read(batch, "customers")}
    order_ids = {row["order_id"] for row in read(batch, "orders")}
    assert all(row["customer_id"] in customer_ids for row in read(batch, "orders"))
    assert all(row["order_id"] in order_ids for row in read(batch, "order_items"))
    assert all(row["order_id"] in order_ids for row in read(batch, "payments"))


def test_every_scenario_has_formatting_noise_for_staging_to_tidy(batches):
    customers = read(batches[Scenario.CLEAN], "customers")
    assert sum(c["email"] != c["email"].lower() for c in customers) == FORMAT_NOISE["uppercase_emails"]
    assert sum(c["country"] != c["country"].upper() for c in customers) == FORMAT_NOISE["lowercase_countries"]
    assert sum(c["last_name"] != c["last_name"].strip() for c in customers) == FORMAT_NOISE["padded_last_names"]


def test_dirty_batch_contains_exactly_the_planted_problems(batches):
    batch = batches[Scenario.DIRTY]
    orders = read(batch, "orders")
    sums = items_total_by_order(batch)

    ids = [row["order_id"] for row in orders]
    assert len(ids) - len(set(ids)) == PLANTED_PROBLEMS["duplicate_order_ids"]
    assert sum(row["customer_id"] == "" for row in orders) == PLANTED_PROBLEMS["missing_customer_ids"]
    assert sum(
        row["customer_id"].isdigit() and int(row["customer_id"]) > N_CUSTOMERS for row in orders
    ) == PLANTED_PROBLEMS["orphan_customers"]
    assert sum(row["order_total"] == "N/A" for row in orders) == PLANTED_PROBLEMS["unparseable_totals"]
    assert sum(row["order_date"] == "yesterday" for row in orders) == PLANTED_PROBLEMS["unparseable_dates"]
    assert sum(
        number(row["order_total"]) is not None and number(row["order_total"]) <= 0 for row in orders
    ) == PLANTED_PROBLEMS["invalid_totals"]

    seen, mismatches = set(), 0
    for row in orders:
        if row["order_id"] in seen:
            continue
        seen.add(row["order_id"])
        total = number(row["order_total"])
        if total is not None and total > 0 and total != sums[row["order_id"]]:
            mismatches += 1
    assert mismatches == PLANTED_PROBLEMS["total_mismatches"]


def test_manifest_records_the_ground_truth(batches):
    assert manifest(batches[Scenario.DIRTY])["planted_problems"] == PLANTED_PROBLEMS
    assert manifest(batches[Scenario.CLEAN])["planted_problems"] == {}
    for scenario, batch in batches.items():
        for table, count in manifest(batch)["row_counts"].items():
            assert len(read(batch, table)) == count, f"{scenario}/{table}"


def test_schema_drift_adds_an_unexpected_column_to_orders(batches):
    orders = read(batches[Scenario.SCHEMA_DRIFT], "orders")
    assert list(orders[0]) == COLUMNS["orders"] + ["coupon_code"]
    assert list(read(batches[Scenario.SCHEMA_DRIFT], "customers")[0]) == COLUMNS["customers"]


def test_volume_drop_has_far_fewer_orders(batches):
    assert len(read(batches[Scenario.VOLUME_DROP], "orders")) == 600


def test_only_the_late_scenario_fixes_a_past_load_time(batches):
    assert manifest(batches[Scenario.LATE])["loaded_at"] == "2026-11-13T02:00:00+00:00"
    for scenario in (Scenario.CLEAN, Scenario.DIRTY, Scenario.SCHEMA_DRIFT, Scenario.VOLUME_DROP):
        assert manifest(batches[scenario])["loaded_at"] is None


@pytest.mark.parametrize("scenario", list(Scenario))
def test_every_scenario_writes_all_files(batches, scenario):
    names = {path.name for path in batches[scenario].iterdir()}
    assert names == {f"{table}.csv" for table in COLUMNS} | {"batch.json"}