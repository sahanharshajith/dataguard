"""Observability check history: freshness and volume."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PrimaryKeyMixin
from app.db.checks import in_enum
from app.models.enums import FreshnessStatus, VolumeStatus


class FreshnessCheck(PrimaryKeyMixin, Base):
    """One freshness measurement for one dataset."""

    __tablename__ = "freshness_checks"
    __table_args__ = (
        in_enum("status", FreshnessStatus, "status_valid"),
        CheckConstraint("age_minutes >= 0", name="age_nonneg"),
        CheckConstraint("expected_refresh_minutes > 0", name="expected_positive"),
        Index("ix_freshness_checks_dataset_id_checked_at", "dataset_id", "checked_at"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    checked_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # NULL when the time of the last load could not be determined (status "unknown").
    last_data_at: Mapped[Optional[datetime]]
    age_minutes: Mapped[Optional[int]]
    status: Mapped[str] = mapped_column(String(10))
    # Snapshot of the configuration in force at check time.
    expected_refresh_minutes: Mapped[int]
    threshold_minutes: Mapped[int]


class VolumeCheck(PrimaryKeyMixin, Base):
    """One row-count measurement for one dataset."""

    __tablename__ = "volume_checks"
    __table_args__ = (
        in_enum("status", VolumeStatus, "status_valid"),
        CheckConstraint("row_count >= 0", name="row_count_nonneg"),
        Index("ix_volume_checks_dataset_id_checked_at", "dataset_id", "checked_at"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    checked_at: Mapped[datetime] = mapped_column(server_default=func.now())
    row_count: Mapped[int] = mapped_column(BigInteger)
    # NULL for a dataset with no history yet.
    baseline_row_count: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(10))
    # Snapshot of the threshold in force at check time.
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))