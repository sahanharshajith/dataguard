# ADR 0004: Run Airflow with LocalExecutor

- **Status:** Proposed
- **Date:** 2026-11-06

## Context
The official Airflow Docker quick-start uses CeleryExecutor, which needs Redis and separate worker containers. DataGuard is a single-developer project that runs locally.

## Decision
Use LocalExecutor: the scheduler runs tasks itself. Run the api-server, scheduler, and dag-processor as separate containers (required by Airflow 3). Omit the triggerer, Celery workers, and Redis. Airflow metadata lives in its own `airflow` database (see ADR 0003).

## Consequences
- Fewer containers and less memory.
- Tasks cannot scale across machines; acceptable for a local portfolio project.
- If deferrable operators are needed later, a triggerer service can be added.