# ADR 0006: One DuckDB file for the RAW, STAGING and ANALYTICS layers

- **Status:** Accepted
- **Date:** 2026-11-23

## Context
DataGuard monitors data in three layers. The platform needs realistic data to monitor, with
planted problems, and the data must be readable by the backend while Airflow writes it.

## Decision
- One DuckDB file with three schemas (`raw`, `staging`, `analytics`) on a named Docker volume.
- RAW loads every column as text plus `_batch_id` and `_loaded_at`; each load replaces the table,
  and the landing CSVs are the permanent history.
- STAGING converts with `TRY_CAST`, standardizes, and de-duplicates, but keeps invalid rows so
  quality rules can still detect them. ANALYTICS flags invalid orders instead of hiding them.
- Airflow writes (one task at a time, via a pool of one slot); the backend opens the file
  read-only.
- Business logic lives in a plain `pipelines/` package with thin DAGs, so it is tested without Airflow.

## Consequences
- A DuckDB file allows one writer or many readers, not both. Checks that run during a load get a
  "file busy" error, which the backend must treat as retryable.
- A batch replaces the previous one, so volume history is tracked by DataGuard's own metadata,
  not by the warehouse.
- Freshness for these tables is measured from `_loaded_at`.