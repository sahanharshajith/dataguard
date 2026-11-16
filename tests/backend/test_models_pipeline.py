"""Database-definition checks for the pipeline tables (no database needed)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models
from app.db.base import Base
from app.models.enums import PipelineRunStatus, TaskStatus


def ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def test_tables_are_registered():
    assert {"pipelines", "pipeline_runs", "pipeline_tasks"} <= set(Base.metadata.tables)


def test_each_dag_is_registered_once():
    assert "uq_pipelines_dag_id" in ddl("pipelines")


def test_resyncing_a_run_from_airflow_cannot_create_a_duplicate():
    assert "uq_pipeline_runs_pipeline_id_airflow_run_id" in ddl("pipeline_runs")


def test_run_status_check_lists_every_status():
    sql = ddl("pipeline_runs")
    assert "ck_pipeline_runs_status_valid" in sql
    for status in PipelineRunStatus:
        assert f"'{status.value}'" in sql


def test_task_status_check_lists_every_status():
    sql = ddl("pipeline_tasks")
    assert "ck_pipeline_tasks_status_valid" in sql
    for status in TaskStatus:
        assert f"'{status.value}'" in sql


def test_a_task_appears_once_per_run():
    assert "uq_pipeline_tasks_pipeline_run_id_task_id" in ddl("pipeline_tasks")


def test_a_run_cannot_end_before_it_starts():
    assert "ck_pipeline_runs_ended_after_started" in ddl("pipeline_runs")


def test_history_is_deleted_with_its_parent():
    assert ddl("pipeline_runs").count("ON DELETE CASCADE") == 1
    assert ddl("pipeline_tasks").count("ON DELETE CASCADE") == 1


def test_first_attempt_is_try_number_one():
    sql = ddl("pipeline_tasks")
    assert "DEFAULT 1" in sql
    assert "ck_pipeline_tasks_try_number_positive" in sql