"""Dataset management tables: `datasets` and `dataset_monitoring_config`."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PrimaryKeyMixin, TimestampMixin
from app.db.checks import in_enum
from app.models.enums import Layer, SourceType


class Dataset(PrimaryKeyMixin, TimestampMixin, Base):
    """One monitored table in one layer (RAW / STAGING / ANALYTICS)."""

    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("layer", "name"),
        in_enum("layer", Layer, "layer_valid"),
        in_enum("source_type", SourceType, "source_type_valid"),
    )

    name: Mapped[str] = mapped_column(String(255))
    layer: Mapped[str] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30))
    source_name: Mapped[Optional[str]] = mapped_column(String(255))
    owner_name: Mapped[Optional[str]] = mapped_column(String(255))
    owner_email: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(500))
    monitoring_enabled: Mapped[bool] = mapped_column(server_default=true())

    # One-to-one. The database deletes the config row (ON DELETE CASCADE),
    # so SQLAlchemy must not try to delete it first.
    config: Mapped[Optional["DatasetMonitoringConfig"]] = relationship(
        back_populates="dataset",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DatasetMonitoringConfig(Base):
    """Thresholds edited on the Configuration page (one row per dataset)."""

    __tablename__ = "dataset_monitoring_config"
    __table_args__ = (
        CheckConstraint("expected_refresh_minutes > 0", name="expected_refresh_positive"),
        CheckConstraint(
            "freshness_threshold_minutes >= expected_refresh_minutes",
            name="freshness_gte_expected",
        ),
        CheckConstraint("volume_change_threshold_pct > 0", name="volume_pct_positive"),
        CheckConstraint("volume_history_window > 0", name="volume_window_positive"),
        CheckConstraint("volume_min_rows >= 0", name="volume_min_rows_nonneg"),
    )

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True
    )
    expected_refresh_minutes: Mapped[int] = mapped_column(server_default=text("1440"))
    freshness_threshold_minutes: Mapped[int] = mapped_column(server_default=text("2880"))
    timestamp_column: Mapped[Optional[str]] = mapped_column(String(255))
    volume_change_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), server_default=text("50")
    )
    volume_history_window: Mapped[int] = mapped_column(server_default=text("7"))
    volume_min_rows: Mapped[int] = mapped_column(BigInteger, server_default=text("1"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    dataset: Mapped[Dataset] = relationship(back_populates="config")