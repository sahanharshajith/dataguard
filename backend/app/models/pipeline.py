"""Pipeline observability tables, synced from the Airflow REST API."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PrimaryKeyMixin
from app.db.checks import in_enum
from app.models.enums import PipelineRunStatus, TaskStatus


class Pipeline(PrimaryKeyMixin, Base):
    """One Airflow DAG."""

    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("dag_id"),)

    dag_id: Mapped[str] = mapped_column(String(250))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PipelineRun(PrimaryKeyMixin, Base):
    """One execution of a DAG."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        # Makes re-syncing from Airflow idempotent: upsert instead of duplicate.
        UniqueConstraint("pipeline_id", "airflow_run_id"),
        in_enum("status", PipelineRunStatus, "status_valid"),
        CheckConstraint("duration_seconds >= 0", name="duration_nonneg"),
        CheckConstraint("ended_at >= started_at", name="ended_after_started"),
        Index("ix_pipeline_runs_pipeline_id_started_at", "pipeline_id", "started_at"),
    )

    pipeline_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pipelines.id", ondelete="CASCADE")
    )
    airflow_run_id: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(10))
    logical_date: Mapped[Optional[datetime]]
    started_at: Mapped[Optional[datetime]]
    ended_at: Mapped[Optional[datetime]]
    duration_seconds: Mapped[Optional[int]]


class PipelineTask(PrimaryKeyMixin, Base):
    """One task instance within a DAG run."""

    __tablename__ = "pipeline_tasks"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "task_id"),
        in_enum("status", TaskStatus, "status_valid"),
        CheckConstraint("try_number >= 1", name="try_number_positive"),
        CheckConstraint("duration_seconds >= 0", name="duration_nonneg"),
    )

    pipeline_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pipeline_runs.id", ondelete="CASCADE")
    )
    task_id: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(20))
    # Retry count = try_number - 1.
    try_number: Mapped[int] = mapped_column(server_default=text("1"))
    max_tries: Mapped[Optional[int]]
    started_at: Mapped[Optional[datetime]]
    ended_at: Mapped[Optional[datetime]]
    duration_seconds: Mapped[Optional[int]]