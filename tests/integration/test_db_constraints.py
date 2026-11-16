"""The database's own rules, tested against a real PostgreSQL.

Each test tries to do something the design forbids and checks that PostgreSQL itself says no
(or does the right thing, for cascades), regardless of what the application code does.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Dataset,
    DatasetMonitoringConfig,
    Pipeline,
    PipelineRun,
    QualityRule,
    QualityRuleResult,
    QualityValidationRun,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def count(session: Session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def dataset_values(**overrides) -> dict:
    values = {"name": "orders", "layer": "raw", "source_type": "csv", "location": "raw.orders"}
    return values | overrides


def make_dataset(session: Session, **overrides) -> Dataset:
    dataset = Dataset(**dataset_values(**overrides))
    session.add(dataset)
    session.flush()
    return dataset


def make_pipeline(session: Session, dag_id: str = "ecommerce_ingestion") -> Pipeline:
    pipeline = Pipeline(dag_id=dag_id)
    session.add(pipeline)
    session.flush()
    return pipeline


def make_rule(session: Session, dataset: Dataset, name: str = "order_id_unique") -> QualityRule:
    rule = QualityRule(
        dataset_id=dataset.id,
        name=name,
        rule_type="unique",
        column_name="order_id",
        dimension="uniqueness",
        severity="high",
    )
    session.add(rule)
    session.flush()
    return rule


def make_run(session: Session, dataset: Dataset) -> QualityValidationRun:
    run = QualityValidationRun(dataset_id=dataset.id, trigger_type="manual", status="succeeded")
    session.add(run)
    session.flush()
    return run


def alert_values(dataset: Dataset, **overrides) -> dict:
    values = {
        "category": "quality",
        "severity": "high",
        "status": "open",
        "title": "Duplicate order ids",
        "dataset_id": dataset.id,
        "dedup_key": "quality:dataset=1:rule=1",
    }
    return values | overrides


def make_alert(session: Session, dataset: Dataset, **overrides) -> Alert:
    alert = Alert(**alert_values(dataset, **overrides))
    session.add(alert)
    session.flush()
    return alert


# datasets


def test_database_fills_in_defaults(session):
    dataset = make_dataset(session)
    session.refresh(dataset)
    assert dataset.id is not None
    assert dataset.monitoring_enabled is True
    assert dataset.created_at.tzinfo is not None  # timestamptz comes back timezone-aware


def test_invalid_layer_is_rejected(session, assert_rejected):
    assert_rejected(
        "ck_datasets_layer_valid",
        lambda: session.add(Dataset(**dataset_values(layer="bronze"))),
    )


def test_same_name_is_allowed_in_another_layer_but_not_twice_in_one(session, assert_rejected):
    make_dataset(session, name="orders", layer="raw")
    make_dataset(session, name="orders", layer="staging")  # allowed
    assert_rejected(
        "uq_datasets_layer_name",
        lambda: session.add(Dataset(**dataset_values(name="orders", layer="raw"))),
    )


def test_freshness_threshold_below_expected_refresh_is_rejected(session, assert_rejected):
    dataset = make_dataset(session)
    assert_rejected(
        "ck_dataset_monitoring_config_freshness_gte_expected",
        lambda: session.add(
            DatasetMonitoringConfig(
                dataset_id=dataset.id,
                expected_refresh_minutes=60,
                freshness_threshold_minutes=30,
            )
        ),
    )


def test_deleting_a_dataset_removes_everything_that_belongs_to_it(session):
    dataset = make_dataset(session)
    session.add(DatasetMonitoringConfig(dataset_id=dataset.id))
    make_rule(session, dataset)
    make_alert(session, dataset)
    session.flush()

    session.execute(delete(Dataset).where(Dataset.id == dataset.id))

    assert count(session, DatasetMonitoringConfig) == 0
    assert count(session, QualityRule) == 0
    assert count(session, Alert) == 0


# alerts (decision DB7)


def test_alert_must_point_at_a_dataset_or_a_pipeline(session, assert_rejected):
    assert_rejected(
        "ck_alerts_has_target",
        lambda: session.add(
            Alert(category="quality", severity="high", status="open", title="Orphan", dedup_key="x")
        ),
    )


def test_second_unresolved_alert_for_the_same_incident_is_rejected(session, assert_rejected):
    dataset = make_dataset(session)
    make_alert(session, dataset)
    assert_rejected(
        "uq_alerts_active_dedup_key",
        lambda: session.add(Alert(**alert_values(dataset))),
    )


def test_an_acknowledged_alert_still_blocks_a_duplicate(session, assert_rejected):
    dataset = make_dataset(session)
    make_alert(session, dataset, status="acknowledged", acknowledged_at=NOW)
    assert_rejected(
        "uq_alerts_active_dedup_key",
        lambda: session.add(Alert(**alert_values(dataset))),
    )


def test_after_resolution_the_same_incident_can_raise_a_new_alert(session):
    dataset = make_dataset(session)
    first = make_alert(session, dataset)
    first.status = "resolved"
    first.resolved_at = NOW
    session.flush()

    second = make_alert(session, dataset)  # must not be rejected

    assert second.id != first.id


def test_resolved_alert_needs_a_resolution_time(session, assert_rejected):
    alert = make_alert(session, make_dataset(session))
    assert_rejected(
        "ck_alerts_resolved_at_matches_status",
        lambda: setattr(alert, "status", "resolved"),
    )


def test_deleting_a_rule_keeps_its_alerts(session):
    dataset = make_dataset(session)
    rule = make_rule(session, dataset)
    alert = make_alert(session, dataset, rule_id=rule.id)

    session.execute(delete(QualityRule).where(QualityRule.id == rule.id))
    session.refresh(alert)

    assert alert.rule_id is None


# quality engine


def test_rule_params_default_to_an_empty_object(session):
    rule = make_rule(session, make_dataset(session))
    session.refresh(rule)
    assert rule.params == {}


def test_run_with_impossible_rule_counts_is_rejected(session, assert_rejected):
    dataset = make_dataset(session)
    assert_rejected(
        "ck_quality_validation_runs_rules_counts_consistent",
        lambda: session.add(
            QualityValidationRun(
                dataset_id=dataset.id,
                trigger_type="manual",
                status="succeeded",
                rules_total=3,
                rules_passed=2,
                rules_failed=2,
            )
        ),
    )


def test_quality_score_above_100_is_rejected(session, assert_rejected):
    dataset = make_dataset(session)
    assert_rejected(
        "ck_quality_validation_runs_quality_score_range",
        lambda: session.add(
            QualityValidationRun(
                dataset_id=dataset.id, trigger_type="manual", status="succeeded", quality_score=101
            )
        ),
    )


def test_a_rule_has_at_most_one_result_per_run(session, assert_rejected):
    dataset = make_dataset(session)
    rule = make_rule(session, dataset)
    run = make_run(session, dataset)
    session.add(QualityRuleResult(run_id=run.id, rule_id=rule.id, status="passed"))
    session.flush()

    assert_rejected(
        "uq_quality_rule_results_run_id_rule_id",
        lambda: session.add(QualityRuleResult(run_id=run.id, rule_id=rule.id, status="failed")),
    )


def test_deleting_a_run_removes_its_results(session):
    dataset = make_dataset(session)
    rule = make_rule(session, dataset)
    run = make_run(session, dataset)
    session.add(QualityRuleResult(run_id=run.id, rule_id=rule.id, status="passed"))
    session.flush()

    session.execute(delete(QualityValidationRun).where(QualityValidationRun.id == run.id))

    assert count(session, QualityRuleResult) == 0


# pipelines


def test_the_same_airflow_run_cannot_be_stored_twice(session, assert_rejected):
    pipeline = make_pipeline(session)
    session.add(PipelineRun(pipeline_id=pipeline.id, airflow_run_id="manual__1", status="success"))
    session.flush()

    assert_rejected(
        "uq_pipeline_runs_pipeline_id_airflow_run_id",
        lambda: session.add(
            PipelineRun(pipeline_id=pipeline.id, airflow_run_id="manual__1", status="failed")
        ),
    )


def test_a_run_cannot_end_before_it_starts(session, assert_rejected):
    pipeline = make_pipeline(session)
    assert_rejected(
        "ck_pipeline_runs_ended_after_started",
        lambda: session.add(
            PipelineRun(
                pipeline_id=pipeline.id,
                airflow_run_id="manual__2",
                status="success",
                started_at=NOW,
                ended_at=NOW - timedelta(minutes=5),
            )
        ),
    )