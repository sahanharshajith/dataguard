"""Database-definition checks for the alert tables (no database needed)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models
from app.db.base import Base
from app.models.enums import AlertCategory, AlertEventType, AlertStatus, Severity


def ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def index_named(table_name: str, name: str):
    return next(i for i in Base.metadata.tables[table_name].indexes if i.name == name)


def test_tables_are_registered():
    assert {"alerts", "alert_events"} <= set(Base.metadata.tables)


def test_category_severity_and_status_are_restricted():
    sql = ddl("alerts")
    for enum_cls in (AlertCategory, Severity, AlertStatus):
        for member in enum_cls:
            assert f"'{member.value}'" in sql


def test_only_one_unresolved_alert_can_exist_per_incident():
    index = index_named("alerts", "uq_alerts_active_dedup_key")
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert "CREATE UNIQUE INDEX" in sql
    assert "WHERE status <> 'resolved'" in sql


def test_every_alert_must_point_at_a_dataset_or_a_pipeline():
    sql = ddl("alerts")
    assert "ck_alerts_has_target" in sql
    assert "dataset_id IS NOT NULL OR pipeline_id IS NOT NULL" in sql


def test_resolved_time_is_set_exactly_when_the_alert_is_resolved():
    assert "ck_alerts_resolved_at_matches_status" in ddl("alerts")


def test_an_acknowledged_alert_has_an_acknowledgement_time():
    assert "ck_alerts_acknowledged_has_time" in ddl("alerts")


def test_foreign_key_delete_behaviour():
    sql = ddl("alerts")
    assert sql.count("ON DELETE CASCADE") == 2
    assert sql.count("ON DELETE SET NULL") == 1


def test_alert_events_are_restricted_cascaded_and_default_to_the_system_actor():
    sql = ddl("alert_events")
    for event_type in AlertEventType:
        assert f"'{event_type.value}'" in sql
    assert "ON DELETE CASCADE" in sql
    assert "DEFAULT 'system'" in sql


def test_alert_indexes_exist():
    names = {index.name for index in Base.metadata.tables["alerts"].indexes}
    assert names == {
        "uq_alerts_active_dedup_key",
        "ix_alerts_status_severity",
        "ix_alerts_dataset_id",
        "ix_alerts_pipeline_id",
        "ix_alerts_rule_id",
    }