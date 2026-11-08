"""Schema tracking tables: snapshots, their columns, and detected changes."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PrimaryKeyMixin
from app.db.checks import in_enum
from app.models.enums import SchemaChangeType


class DatasetSchema(PrimaryKeyMixin, Base):
    """A snapshot of a dataset's structure. The current schema is the highest version."""

    __tablename__ = "dataset_schemas"
    __table_args__ = (
        # Also serves as the index on dataset_id (it is the leading column).
        UniqueConstraint("dataset_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    version: Mapped[int]
    schema_hash: Mapped[str] = mapped_column(CHAR(64))
    captured_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DatasetColumn(PrimaryKeyMixin, Base):
    """One column inside one schema snapshot."""

    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint("schema_id", "name"),
        UniqueConstraint("schema_id", "position"),
        CheckConstraint("position >= 1", name="position_positive"),
    )

    schema_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dataset_schemas.id", ondelete="CASCADE")
    )
    position: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(100))
    is_nullable: Mapped[bool]


class SchemaChange(PrimaryKeyMixin, Base):
    """One detected difference between two consecutive schema snapshots."""

    __tablename__ = "schema_changes"
    __table_args__ = (
        in_enum("change_type", SchemaChangeType, "change_type_valid"),
        Index("ix_schema_changes_dataset_id_detected_at", "dataset_id", "detected_at"),
        Index("ix_schema_changes_from_schema_id", "from_schema_id"),
        Index("ix_schema_changes_to_schema_id", "to_schema_id"),
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("datasets.id", ondelete="CASCADE")
    )
    # NULL for the very first snapshot, which has no predecessor.
    from_schema_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("dataset_schemas.id", ondelete="CASCADE")
    )
    to_schema_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dataset_schemas.id", ondelete="CASCADE")
    )
    change_type: Mapped[str] = mapped_column(String(30))
    column_name: Mapped[str] = mapped_column(String(255))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(server_default=func.now())