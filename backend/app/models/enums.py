"""
Allowed values for every fixed-choice column.

Each enum is mirrored by a CHECK constraint in the database (see app/db/checks.py),
so the application and the database cannot disagree about what is valid.
"""

from enum import StrEnum


class Layer(StrEnum):
    RAW = "raw"
    STAGING = "staging"
    ANALYTICS = "analytics"


class SourceType(StrEnum):
    API = "api"
    DATABASE = "database"
    CSV = "csv"
    APPLICATION = "application"


class RuleType(StrEnum):
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    DATA_TYPE = "data_type"
    ACCEPTED_VALUES = "accepted_values"
    NUMERIC_RANGE = "numeric_range"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    CUSTOM_SQL = "custom_sql"
    SCHEMA = "schema"


class QualityDimension(StrEnum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    PIPELINE = "pipeline"


class ValidationRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RuleResultStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    WARNING = "warning"
    STALE = "stale"
    UNKNOWN = "unknown"


class VolumeStatus(StrEnum):
    NORMAL = "normal"
    SPIKE = "spike"
    DROP = "drop"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class SchemaChangeType(StrEnum):
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_RENAMED = "column_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABILITY_CHANGED = "nullability_changed"


class PipelineRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    UP_FOR_RETRY = "up_for_retry"


class AlertCategory(StrEnum):
    QUALITY = "quality"
    FRESHNESS = "freshness"
    SCHEMA = "schema"
    VOLUME = "volume"
    PIPELINE = "pipeline"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertEventType(StrEnum):
    OPENED = "opened"
    OCCURRENCE = "occurrence"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"