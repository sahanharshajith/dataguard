"""Database-definition checks for the freshness and volume tables (no database needed)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models
from app.db.base import Base
from app.models.enums import FreshnessStatus, VolumeStatus


def ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def columns(table_name: str):
    return Base.metadata.tables[table_name].c


def index_names(table_name: str) -> set[str]:
    return {index.name for index in Base.metadata.tables[table_name].indexes}


def test_tables_are_registered():
    assert {"freshness_checks", "volume_checks"} <= set(Base.metadata.tables)


def test_freshness_status_check_lists_every_status():
    sql = ddl("freshness_checks")
    assert "ck_freshness_checks_status_valid" in sql
    for status in FreshnessStatus:
        assert f"'{status.value}'" in sql


def test_freshness_keeps_the_thresholds_in_force_at_check_time():
    cols = columns("freshness_checks")
    assert not cols.expected_refresh_minutes.nullable
    assert not cols.threshold_minutes.nullable


def test_freshness_last_data_time_may_be_unknown():
    assert columns("freshness_checks").last_data_at.nullable


def test_volume_status_check_lists_every_status():
    sql = ddl("volume_checks")
    assert "ck_volume_checks_status_valid" in sql
    for status in VolumeStatus:
        assert f"'{status.value}'" in sql


def test_volume_baseline_is_optional_because_new_datasets_have_no_history():
    cols = columns("volume_checks")
    assert cols.baseline_row_count.nullable
    assert cols.change_pct.nullable
    assert not cols.row_count.nullable


def test_row_count_cannot_be_negative():
    assert "ck_volume_checks_row_count_nonneg" in ddl("volume_checks")


def test_latest_check_indexes_exist():
    assert "ix_freshness_checks_dataset_id_checked_at" in index_names("freshness_checks")
    assert "ix_volume_checks_dataset_id_checked_at" in index_names("volume_checks")