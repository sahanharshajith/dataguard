"""Alerting tables: alerts and their append-only event history."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PrimaryKeyMixin
from app.db.checks import in_enum
from app.models.enums import AlertCategory, AlertEventType, AlertStatus, Severity


class Alert(PrimaryKeyMixin, Base):
    """One incident. Repeats of the same ongoing problem update this row, not add new ones."""

    __tablename__ = "alerts"
    __table_args__ = (
        in_enum("category", AlertCategory, "category_valid"),
        in_enum("severity", Severity, "severity_valid"),
        in_enum("status", AlertStatus, "status_valid"),
        CheckConstraint("dataset_id IS NOT NULL OR pipeline_id IS NOT NULL", name="has_target"),
        CheckConstraint("occurrence_count >= 1", name="occurrence_count_positive"),
        CheckConstraint(
            "(status = 'resolved') = (resolved_at IS NOT NULL)",
            name="resolved_at_matches_status",
        ),
        CheckConstraint(
            "status <> 'acknowledged' OR acknowledged_at IS NOT NULL",
            name="acknowledged_has_time",
        ),
        Index(
            "uq_alerts_active_dedup_key",
            "dedup_key",
            unique=True,
            postgresql_where=text("status <> 'resolved'"),
        ),
        Index("ix_alerts_status_severity", "status", "severity"),
        Index("ix_alerts_dataset_id", "dataset_id"),
        Index("ix_alerts_pipeline_id", "pipeline_id"),
        Index("ix_alerts_rule_id", "rule_id"),
    )

    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    dataset_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    pipeline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pipelines.id", ondelete="CASCADE")
    )
    rule_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("quality_rules.id", ondelete="SET NULL")
    )
    dedup_key: Mapped[str] = mapped_column(String(500))
    first_detected_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_detected_at: Mapped[datetime] = mapped_column(server_default=func.now())
    occurrence_count: Mapped[int] = mapped_column(server_default=text("1"))
    acknowledged_at: Mapped[Optional[datetime]]
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255))
    resolved_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AlertEvent(PrimaryKeyMixin, Base):
    """Append-only history of what happened to an alert."""

    __tablename__ = "alert_events"
    __table_args__ = (
        in_enum("event_type", AlertEventType, "event_type_valid"),
        Index("ix_alert_events_alert_id_created_at", "alert_id", "created_at"),
    )

    alert_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alerts.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(255), server_default=text("'system'"))
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())