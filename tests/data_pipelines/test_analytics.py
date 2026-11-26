"""Acceptance tests for the ANALYTICS layer (build_analytics in pipelines/etl/analytics.py)."""

import duckdb
import pytest

from pipelines.etl.analytics import build_analytics
from pipelines.etl.raw import load_batch_to_raw
from pipelines.etl.staging import build_staging
from pipelines.generator.generate import PLANTED_PROBLEMS, Scenario

TABLES = ["dim_customers", "dim_products", "fct_orders", "daily_sales"]
METADATA = {"_batch_id", "_loaded_at"}

EXPECTED_COLUMNS = {
    "dim_customers": {"customer_id", "full_name", "email", "country", "signup_date",
                      "order_count", "total_spent"},
    "dim_products": {"product_id", "product_name", "category", "unit_price", "units_sold"},
    "fct_orders": {"order_id", "customer_id", "order_date", "status", "order_total",
                   "items_total", "item_count", "payment_status", "is_valid"},
    "daily_sales": {"order_date", "order_count", "revenue", "avg_order_value"},
}

# A "sale" counts toward revenue: a valid order that was not cancelled.
SALE = "is_valid AND status <> 'cancelled'"


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def column_names(con, table):
    return {row[0] for row in con.execute(f"DESCRIBE {table}").fetchall()}


def build_all(con):
    build_staging(con)
    build_analytics(con)


@pytest.fixture(scope="module")
def dirty(batches):
    con = duckdb.connect()
    load_batch_to_raw(con, batches[Scenario.DIRTY])
    build_all(con)
    yield con
    con.close()


@pytest.fixture(scope="module")
def clean(batches):
    con = duckdb.connect()
    load_batch_to_raw(con, batches[Scenario.CLEAN])
    build_all(con)
    yield con
    con.close()


def test_every_analytics_table_exists(dirty):
    names = {
        row[0]
        for row in dirty.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics'"
        ).fetchall()
    }
    assert names == set(TABLES)


@pytest.mark.parametrize("table", TABLES)
def test_columns_match_the_contract(dirty, table):
    assert column_names(dirty, f"analytics.{table}") == EXPECTED_COLUMNS[table] | METADATA


# fct_orders

def test_fct_orders_has_exactly_one_row_per_order(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.fct_orders") == 5000
    assert scalar(dirty, "SELECT count(DISTINCT order_id) FROM analytics.fct_orders") == 5000


def test_is_valid_is_always_true_or_false_never_null(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.fct_orders WHERE is_valid IS NULL") == 0


def test_clean_data_is_entirely_valid(clean):
    assert scalar(clean, "SELECT count(*) FROM analytics.fct_orders WHERE NOT is_valid") == 0


def test_exactly_the_planted_bad_orders_are_invalid(dirty):
    planted = sum(PLANTED_PROBLEMS.values()) - PLANTED_PROBLEMS["duplicate_order_ids"]
    assert scalar(dirty, "SELECT count(*) FROM analytics.fct_orders WHERE NOT is_valid") == planted


def test_item_counts_and_totals_add_up(dirty):
    assert scalar(dirty, "SELECT sum(item_count) FROM analytics.fct_orders") == scalar(
        dirty, "SELECT count(*) FROM staging.order_items"
    )
    assert scalar(
        dirty, "SELECT count(*) FROM analytics.fct_orders WHERE is_valid AND items_total <> order_total"
    ) == 0


def test_every_order_carries_its_payment_status(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.fct_orders WHERE payment_status IS NULL") == 0


# dimensions

def test_dim_customers_has_one_row_per_customer_with_no_null_measures(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.dim_customers") == 1000
    assert scalar(dirty, "SELECT count(DISTINCT customer_id) FROM analytics.dim_customers") == 1000
    assert scalar(
        dirty,
        "SELECT count(*) FROM analytics.dim_customers WHERE order_count IS NULL OR total_spent IS NULL",
    ) == 0


def test_customer_measures_only_count_valid_orders(dirty):
    assert scalar(dirty, "SELECT sum(order_count) FROM analytics.dim_customers") == scalar(
        dirty, "SELECT count(*) FROM analytics.fct_orders WHERE is_valid"
    )
    assert scalar(dirty, "SELECT sum(total_spent) FROM analytics.dim_customers") == scalar(
        dirty, f"SELECT sum(order_total) FROM analytics.fct_orders WHERE {SALE}"
    )


def test_dim_products_has_one_row_per_product_and_counts_units_sold(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.dim_products") == 100
    assert scalar(dirty, "SELECT count(*) FROM analytics.dim_products WHERE units_sold IS NULL") == 0
    expected = scalar(
        dirty,
        """
        SELECT sum(i.quantity)
        FROM staging.order_items i
        JOIN analytics.fct_orders o USING (order_id)
        WHERE o.is_valid AND o.status <> 'cancelled'
        """,
    )
    assert scalar(dirty, "SELECT sum(units_sold) FROM analytics.dim_products") == expected


# daily_sales

def test_daily_sales_has_one_row_per_date_and_no_null_dates(dirty):
    assert scalar(dirty, "SELECT count(*) FROM analytics.daily_sales WHERE order_date IS NULL") == 0
    assert scalar(dirty, "SELECT count(*) FROM analytics.daily_sales") == scalar(
        dirty, "SELECT count(DISTINCT order_date) FROM analytics.daily_sales"
    )


def test_daily_sales_adds_up_to_the_sales_in_fct_orders(dirty):
    assert scalar(dirty, "SELECT sum(order_count) FROM analytics.daily_sales") == scalar(
        dirty, f"SELECT count(*) FROM analytics.fct_orders WHERE {SALE}"
    )
    assert scalar(dirty, "SELECT sum(revenue) FROM analytics.daily_sales") == scalar(
        dirty, f"SELECT sum(order_total) FROM analytics.fct_orders WHERE {SALE}"
    )


def test_average_order_value_is_revenue_divided_by_orders(dirty):
    wrong = scalar(
        dirty,
        "SELECT count(*) FROM analytics.daily_sales WHERE abs(avg_order_value - revenue / order_count) > 0.01",
    )
    assert wrong == 0


def test_invalid_orders_cannot_make_revenue_negative(dirty):
    assert scalar(dirty, "SELECT min(revenue) FROM analytics.daily_sales") > 0


# all tables

@pytest.mark.parametrize("table", TABLES)
def test_batch_metadata_is_carried_through(dirty, table):
    batch_ids = [r[0] for r in dirty.execute(f"SELECT DISTINCT _batch_id FROM analytics.{table}").fetchall()]
    assert batch_ids == ["2026-11-16_dirty"]
    assert scalar(dirty, f"SELECT count(*) FROM analytics.{table} WHERE _loaded_at IS NULL") == 0


def test_building_twice_gives_the_same_result_and_reports_row_counts(raw_con):
    con = raw_con(Scenario.DIRTY)
    build_staging(con)
    first = build_analytics(con)
    second = build_analytics(con)
    assert first == second
    assert first == {table: scalar(con, f"SELECT count(*) FROM analytics.{table}") for table in TABLES}