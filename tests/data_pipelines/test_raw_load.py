import json
import shutil
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from pipelines.etl.raw import TABLES, load_batch_to_raw
from pipelines.generator.generate import COLUMNS, Scenario


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def column_types(con, table):
    return {row[0]: row[1] for row in con.execute(f"DESCRIBE {table}").fetchall()}


def test_raw_tables_have_the_source_columns_plus_metadata(raw_con):
    con = raw_con(Scenario.CLEAN)
    for table in TABLES:
        assert list(column_types(con, f"raw.{table}")) == COLUMNS[table] + ["_batch_id", "_loaded_at"]


def test_source_columns_are_loaded_as_text(raw_con):
    con = raw_con(Scenario.CLEAN)
    for table in TABLES:
        types = column_types(con, f"raw.{table}")
        for column in COLUMNS[table]:
            assert types[column] == "VARCHAR", f"raw.{table}.{column} is {types[column]}"
    assert column_types(con, "raw.orders")["_loaded_at"] == "TIMESTAMP"


def test_row_counts_are_returned(batches):
    con = duckdb.connect()
    counts = load_batch_to_raw(con, batches[Scenario.CLEAN])
    expected = json.loads((batches[Scenario.CLEAN] / "batch.json").read_text())["row_counts"]
    assert counts == expected


def test_bad_values_survive_raw_untouched(raw_con):
    con = raw_con(Scenario.DIRTY)
    assert scalar(con, "SELECT count(*) FROM raw.orders WHERE order_total = 'N/A'") == 15
    assert scalar(con, "SELECT count(*) FROM raw.orders WHERE order_date = 'yesterday'") == 15


def test_duplicates_are_loaded_untouched(raw_con):
    con = raw_con(Scenario.DIRTY)
    assert scalar(con, "SELECT count(*) FROM raw.orders") == 5025
    assert scalar(con, "SELECT count(DISTINCT order_id) FROM raw.orders") == 5000


def test_empty_csv_fields_become_null(raw_con):
    con = raw_con(Scenario.DIRTY)
    assert scalar(con, "SELECT count(*) FROM raw.orders WHERE customer_id IS NULL") == 40


def test_formatting_noise_is_still_there_in_raw(raw_con):
    con = raw_con(Scenario.CLEAN)
    assert scalar(con, "SELECT count(*) FROM raw.customers WHERE email <> lower(email)") == 50
    assert scalar(con, "SELECT count(*) FROM raw.customers WHERE country <> upper(country)") == 50


def test_unexpected_columns_are_kept(raw_con):
    con = raw_con(Scenario.SCHEMA_DRIFT)
    assert "coupon_code" in column_types(con, "raw.orders")


def test_each_load_replaces_the_previous_batch(batches):
    con = duckdb.connect()
    load_batch_to_raw(con, batches[Scenario.CLEAN])
    load_batch_to_raw(con, batches[Scenario.VOLUME_DROP])
    assert scalar(con, "SELECT count(*) FROM raw.orders") == 600
    batch_ids = [row[0] for row in con.execute("SELECT DISTINCT _batch_id FROM raw.orders").fetchall()]
    assert batch_ids == ["2026-11-16_volume_drop"]


def test_late_batch_uses_the_load_time_from_its_manifest(raw_con):
    con = raw_con(Scenario.LATE)
    loaded = [row[0] for row in con.execute("SELECT DISTINCT _loaded_at FROM raw.orders").fetchall()]
    assert loaded == [datetime(2026, 11, 13, 2, 0)]


def test_normal_batch_is_stamped_with_the_ingestion_time(raw_con):
    con = raw_con(Scenario.CLEAN)
    loaded = scalar(con, "SELECT max(_loaded_at) FROM raw.orders")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(now - loaded) < timedelta(minutes=5)


def test_a_failed_load_leaves_the_previous_data_untouched(batches, tmp_path):
    con = duckdb.connect()
    load_batch_to_raw(con, batches[Scenario.CLEAN])

    broken = tmp_path / "broken"
    shutil.copytree(batches[Scenario.VOLUME_DROP], broken)
    (broken / "payments.csv").unlink()  # the last table to load, so earlier ones already ran

    with pytest.raises(duckdb.Error):
        load_batch_to_raw(con, broken)

    assert scalar(con, "SELECT count(*) FROM raw.orders") == 5000
    assert scalar(con, "SELECT min(_batch_id) FROM raw.orders") == "2026-11-16_clean"