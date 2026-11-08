"""Database-definition checks for the schema tracking tables (no database needed)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models
from app.db.base import Base
from app.models.enums import SchemaChangeType


def ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def index_names(table_name: str) -> set[str]:
    return {index.name for index in Base.metadata.tables[table_name].indexes}


def test_tables_are_registered():
    assert {"dataset_schemas", "dataset_columns", "schema_changes"} <= set(Base.metadata.tables)


def test_a_dataset_cannot_have_two_snapshots_with_the_same_version():
    assert "uq_dataset_schemas_dataset_id_version" in ddl("dataset_schemas")


def test_a_snapshot_cannot_repeat_a_column_name_or_position():
    sql = ddl("dataset_columns")
    assert "uq_dataset_columns_schema_id_name" in sql
    assert "uq_dataset_columns_schema_id_position" in sql


def test_schema_hash_is_a_fixed_length_sha256_string():
    assert "schema_hash CHAR(64) NOT NULL" in ddl("dataset_schemas")


def test_change_type_check_lists_every_enum_value():
    sql = ddl("schema_changes")
    assert "ck_schema_changes_change_type_valid" in sql
    for change_type in SchemaChangeType:
        assert f"'{change_type.value}'" in sql


def test_first_snapshot_may_have_no_previous_schema():
    sql = ddl("schema_changes")
    assert "to_schema_id BIGINT NOT NULL" in sql
    assert "from_schema_id BIGINT NOT NULL" not in sql


def test_schema_changes_have_the_planned_indexes():
    assert index_names("schema_changes") == {
        "ix_schema_changes_dataset_id_detected_at",
        "ix_schema_changes_from_schema_id",
        "ix_schema_changes_to_schema_id",
    }