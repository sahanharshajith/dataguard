"""Acceptance tests for the STAGING layer (build_staging in pipelines/etl/staging.py)."""

import duckdb
import pytest

from pipelines.etl.raw import load_batch_to_raw
from pipelines.etl.staging import build_staging
from pipelines.generator.generate import Scenario

TABLES = ["customers", "products", "orders", "order_items", "payments"]
METADATA = {"_batch_id", "_loaded_at"}

# Each value is the start of the type name DuckDB reports (DECIMAL(12,2) starts with DECIMAL).
EXPECTED_TYPES = {
    "customers": {
        "customer_id": "BIGINT", "first_name": "VARCHAR", "last_name": "VARCHAR",
        "email": "VARCHAR", "country": "VARCHAR", "signup_date": "DATE",
    },
    "products": {
        "product_id": "BIGINT", "product_name": "VARCHAR", "category": "VARCHAR",
        "unit_price": "DECIMAL",
    },
    "orders": {
        "order_id": "BIGINT", "customer_id": "BIGINT", "order_date": "DATE",
        "status": "VARCHAR", "order_total": "DECIMAL",
    },
    "order_items": {
        "order_item_id": "BIGINT", "order_id": "BIGINT", "product_id": "BIGINT",
        "quantity": "INTEGER", "unit_price": "DECIMAL", "line_total": "DECIMAL",
    },
    "payments": {
        "payment_id": "BIGINT", "order_id": "BIGINT", "payment_method": "VARCHAR",
        "amount": "DECIMAL", "paid_at": "TIMESTAMP", "payment_status": "VARCHAR",
    },
}


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def column_types(con, table):
    return {row[0]: row[1] for row in con.execute(f"DESCRIBE {table}").fetchall()}


@pytest.fixture(scope="module")
def staged(batches):
    """A warehouse loaded with the DIRTY batch and staged once; tests only read from it."""
    con = duckdb.connect()
    load_batch_to_raw(con, batches[Scenario.DIRTY])
    build_staging(con)
    yield con
    con.close()


def test_every_staging_table_exists(staged):
    names = {
        row[0]
        for row in staged.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
        ).fetchall()
    }
    assert names == set(TABLES)


@pytest.mark.parametrize("table", TABLES)
def test_columns_have_the_expected_names_and_types(staged, table):
    types = column_types(staged, f"staging.{table}")
    expected = EXPECTED_TYPES[table]
    assert set(types) == set(expected) | METADATA
    for column, expected_type in expected.items():
        assert types[column].startswith(expected_type), f"{table}.{column} is {types[column]}"
    assert types["_loaded_at"] == "TIMESTAMP"


def test_duplicate_orders_are_removed(staged):
    assert scalar(staged, "SELECT count(*) FROM staging.orders") == 5000
    assert scalar(staged, "SELECT count(DISTINCT order_id) FROM staging.orders") == 5000


def test_tables_without_duplicates_keep_every_row(staged):
    for table in ["customers", "products", "order_items", "payments"]:
        raw_rows = scalar(staged, f"SELECT count(*) FROM raw.{table}")
        assert scalar(staged, f"SELECT count(*) FROM staging.{table}") == raw_rows, table
    assert scalar(staged, "SELECT count(DISTINCT customer_id) FROM staging.customers") == 1000


def test_unparseable_values_become_null_instead_of_failing(staged):
    assert scalar(staged, "SELECT count(*) FROM staging.orders WHERE order_total IS NULL") == 15
    assert scalar(staged, "SELECT count(*) FROM staging.orders WHERE order_date IS NULL") == 15


def test_missing_customer_ids_stay_null(staged):
    assert scalar(staged, "SELECT count(*) FROM staging.orders WHERE customer_id IS NULL") == 40


def test_invalid_rows_are_kept_not_rejected(staged):
    assert scalar(staged, "SELECT count(*) FROM staging.orders WHERE order_total <= 0") == 30
    orphans = scalar(
        staged,
        """
        SELECT count(*) FROM staging.orders
        WHERE customer_id IS NOT NULL
          AND customer_id NOT IN (SELECT customer_id FROM staging.customers)
        """,
    )
    assert orphans == 35


def test_text_is_standardized(staged):
    assert scalar(staged, "SELECT count(*) FROM staging.customers WHERE email <> lower(trim(email))") == 0
    assert scalar(
        staged,
        "SELECT count(*) FROM staging.customers WHERE country <> upper(trim(country)) OR length(country) <> 2",
    ) == 0
    assert scalar(staged, "SELECT count(*) FROM staging.customers WHERE last_name <> trim(last_name)") == 0


def test_converting_types_does_not_change_the_values(staged):
    staged_sum = scalar(staged, "SELECT sum(order_total) FROM staging.orders")
    raw_sum = scalar(
        staged,
        "SELECT sum(TRY_CAST(order_total AS DECIMAL(12, 2))) FROM (SELECT DISTINCT * FROM raw.orders)",
    )
    assert staged_sum == raw_sum
    assert scalar(staged, "SELECT sum(line_total) FROM staging.order_items") == scalar(
        staged, "SELECT sum(CAST(line_total AS DECIMAL(12, 2))) FROM raw.order_items"
    )


def test_batch_metadata_is_carried_over(staged):
    for table in TABLES:
        batch_ids = [r[0] for r in staged.execute(f"SELECT DISTINCT _batch_id FROM staging.{table}").fetchall()]
        assert batch_ids == ["2026-11-16_dirty"], table
        assert scalar(staged, f"SELECT count(*) FROM staging.{table} WHERE _loaded_at IS NULL") == 0


def test_an_unexpected_raw_column_does_not_break_staging(raw_con):
    con = raw_con(Scenario.SCHEMA_DRIFT)
    build_staging(con)
    assert "coupon_code" not in column_types(con, "staging.orders")
    assert scalar(con, "SELECT count(*) FROM staging.orders") == 5000


def test_building_twice_gives_the_same_result_and_reports_row_counts(raw_con):
    con = raw_con(Scenario.DIRTY)
    first = build_staging(con)
    second = build_staging(con)
    assert first == second
    assert first == {table: scalar(con, f"SELECT count(*) FROM staging.{table}") for table in TABLES}