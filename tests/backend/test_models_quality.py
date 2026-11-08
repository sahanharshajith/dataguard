"""Database-definition checks for the quality engine tables (no database needed)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models
from app.db.base import Base
from app.models.enums import QualityDimension, RuleResultStatus, RuleType, Severity


def ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def test_tables_are_registered():
    expected = {"quality_rules", "quality_validation_runs", "quality_rule_results"}
    assert expected <= set(Base.metadata.tables)


def test_rule_type_check_lists_every_rule_type():
    sql = ddl("quality_rules")
    assert "ck_quality_rules_rule_type_valid" in sql
    for rule_type in RuleType:
        assert f"'{rule_type.value}'" in sql


def test_rule_dimension_and_severity_are_restricted():
    sql = ddl("quality_rules")
    for dimension in QualityDimension:
        assert f"'{dimension.value}'" in sql
    for severity in Severity:
        assert f"'{severity.value}'" in sql


def test_rule_names_are_unique_within_a_dataset():
    assert "uq_quality_rules_dataset_id_name" in ddl("quality_rules")


def test_rule_params_are_jsonb_defaulting_to_an_empty_object():
    sql = ddl("quality_rules")
    assert "JSONB" in sql
    assert "'{}'::jsonb" in sql


def test_every_score_is_limited_to_0_through_100():
    sql = ddl("quality_validation_runs")
    for column in (
        "quality_score",
        "completeness_score",
        "uniqueness_score",
        "validity_score",
        "consistency_score",
    ):
        assert f"ck_quality_validation_runs_{column}_range" in sql


def test_rule_counts_must_be_consistent():
    assert "ck_quality_validation_runs_rules_counts_consistent" in ddl("quality_validation_runs")


def test_run_history_index_exists():
    names = {index.name for index in Base.metadata.tables["quality_validation_runs"].indexes}
    assert "ix_quality_validation_runs_dataset_id_started_at" in names


def test_one_result_per_rule_per_run():
    assert "uq_quality_rule_results_run_id_rule_id" in ddl("quality_rule_results")


def test_result_status_check_lists_every_status():
    sql = ddl("quality_rule_results")
    for status in RuleResultStatus:
        assert f"'{status.value}'" in sql


def test_results_are_deleted_with_their_run_and_their_rule():
    assert ddl("quality_rule_results").count("ON DELETE CASCADE") == 2