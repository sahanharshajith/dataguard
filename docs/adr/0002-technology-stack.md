# ADR 0002: Technology stack

- **Status:** Accepted
- **Date:** 2026-11-04

## Context
DataGuard must orchestrate pipelines, validate data, store metadata and analytical data, expose an API, and provide a dashboard, and it must be runnable locally by one developer.

## Decision
| Concern | Choice |
|---------|--------|
| Orchestration | Apache Airflow |
| Data validation | Great Expectations (GX Core) |
| Metadata and operational store | PostgreSQL |
| Analytical layers (RAW/STAGING/ANALYTICS) | DuckDB |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Testing | pytest |
| Packaging | Docker and Docker Compose |

## Consequences
- PostgreSQL for transactional metadata and DuckDB for analytical queries uses each tool for what it does best.
- Airflow and Great Expectations are widely used in industry, so the project reflects real data-engineering practice.
- Airflow adds infrastructure weight; we limit it by using LocalExecutor.
- Further technologies (OpenLineage, Marquez, Prometheus, Grafana) are deferred until the MVP works.
