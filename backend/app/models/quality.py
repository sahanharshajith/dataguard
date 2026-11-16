"""Quality engine tables: rules, validation runs, and per-rule results."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PrimaryKeyMixin, TimestampMixin
from app.db.checks import in_enum
from app.models.enums import (
    QualityDimension,
    RuleResultStatus,
    RuleType,
    Severity,
    ValidationRunStatus,
    ValidationTrigger,
)

SCORE_COLUMNS = (
    "quality_score",
    "completeness_score",
    "uniqueness_score",
    "validity_score",
    "consistency_score",
)


class QualityRule(PrimaryKeyMixin, TimestampMixin, Base):
    """A configured check on a dataset."""

    __tablename__ = "quality_rules"
    __table_args__ = (
        UniqueConstraint("dataset_id", "name"),
        in_enum("rule_type", RuleType, "rule_type_valid"),
        in_enum("dimension", QualityDimension, "dimension_valid"),
        in_enum("severity", Severity, "severity_valid"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    rule_type: Mapped[str] = mapped_column(String(30))
    column_name: Mapped[Optional[str]] = mapped_column(String(255))
    params: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    dimension: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    is_enabled: Mapped[bool] = mapped_column(server_default=true())


class QualityValidationRun(PrimaryKeyMixin, Base):
    """One execution of all enabled rules for one dataset."""

    __tablename__ = "quality_validation_runs"
    __table_args__ = (
        in_enum("trigger_type", ValidationTrigger, "trigger_type_valid"),
        in_enum("status", ValidationRunStatus, "status_valid"),
        CheckConstraint(
            "rules_passed >= 0 AND rules_failed >= 0 "
            "AND rules_passed + rules_failed <= rules_total",
            name="rules_counts_consistent",
        ),
        *(
            CheckConstraint(f"{column} BETWEEN 0 AND 100", name=f"{column}_range")
            for column in SCORE_COLUMNS
        ),
        Index("ix_quality_validation_runs_dataset_id_started_at", "dataset_id", "started_at"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    trigger_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[Optional[datetime]]
    rules_total: Mapped[int] = mapped_column(server_default=text("0"))
    rules_passed: Mapped[int] = mapped_column(server_default=text("0"))
    rules_failed: Mapped[int] = mapped_column(server_default=text("0"))
    quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    completeness_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    uniqueness_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    validity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    consistency_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    scoring_weights: Mapped[Optional[dict[str, Any]]]
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class QualityRuleResult(PrimaryKeyMixin, Base):
    """The outcome of one rule within one validation run."""

    __tablename__ = "quality_rule_results"
    __table_args__ = (
        UniqueConstraint("run_id", "rule_id"),
        in_enum("status", RuleResultStatus, "status_valid"),
        CheckConstraint("failed_percent BETWEEN 0 AND 100", name="failed_percent_range"),
        CheckConstraint("failed_rows <= checked_rows", name="failed_lte_checked"),
        Index("ix_quality_rule_results_rule_id", "rule_id"),
    )

    run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quality_validation_runs.id", ondelete="CASCADE")
    )
    rule_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quality_rules.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(10))
    checked_rows: Mapped[Optional[int]] = mapped_column(BigInteger)
    failed_rows: Mapped[Optional[int]] = mapped_column(BigInteger)
    failed_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    details: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())