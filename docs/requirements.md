# DataGuard – Requirements (Phase 1)

## Problem statement
Data pipelines can complete successfully while delivering unreliable data (duplicates, missing values, invalid values, schema drift, delays, volume swings). These failures are usually silent and discovered late, by stakeholders. DataGuard detects and surfaces them automatically.

## Objectives
| ID | Objective |
|----|-----------|
| O1 | Detect data quality problems automatically |
| O2 | Quantify quality with a transparent, documented score |
| O3 | Detect freshness, schema, and volume problems |
| O4 | Observe Apache Airflow pipelines |
| O5 | Alert without noise (one alert per ongoing incident) |
| O6 | Be reproducible: runs with Docker Compose, documented and tested |

## Actors
Data Engineer (primary), Data Analyst, Data Owner, Platform Admin (post-MVP), Apache Airflow, Great Expectations, source systems.

## Functional requirements
- **Dataset management (FR-DS):** register datasets with name, description, source, owner, location, layer; store schema; enable/disable monitoring.
- **Quality rules (FR-QR):** NOT NULL, uniqueness, data type, accepted values, numeric range, referential integrity, custom SQL, schema; attach to datasets; severity per rule.
- **Quality engine (FR-QE):** run rules through Great Expectations; store runs and results; identify failures; generate reports.
- **Quality score (FR-SC):** completeness, uniqueness, validity, consistency; configurable weights; score history.
- **Freshness (FR-FR):** expected frequency, thresholds, last successful ingestion, status, history.
- **Schema change detection (FR-SCH):** snapshots; added, removed, type-changed columns; nullable changes; likely renames.
- **Volume anomalies (FR-VOL):** row counts per run; empty dataset, spike, and drop detection via thresholds and rolling history.
- **Pipeline observability (FR-PL):** DAG/task status, duration, retries, last success, history.
- **Alerts (FR-AL):** alerts for all detector types; severity, category, reference, timestamps, acknowledge/resolve; deduplication; in-app only for the MVP.
- **Dashboard (FR-UI):** Overview, Dataset Details, Pipeline Monitoring, Quality Issues, Alert Management, Dataset Configuration.

## Non-functional requirements
Reliability (a failing check never crashes monitoring), safety (read-only access to Airflow and data), performance, maintainability (layered backend, type hints, tests), reproducibility (one-command local start), security (secrets in env vars, validated input, parameterized SQL), extensibility (new rule/check types), observability (structured logging), usability, documentation.

## MVP scope
Everything listed above, with an e-commerce demo, Docker Compose, a pytest suite, README, and ADRs.

## Postponed
Authentication/RBAC, email/Slack/webhook notifications, OpenLineage/Marquez, Prometheus/Grafana, statistical or ML anomaly detection, multi-tenancy, cloud deployment, rule suggestions.

## Working assumptions
Monitored layers (RAW/STAGING/ANALYTICS) live in DuckDB; platform metadata lives in PostgreSQL; no authentication in the MVP; Airflow is observed through its REST API (read-only); LocalExecutor; Recharts for charts; local Docker Compose deployment. Detailed architecture decisions will be recorded as ADRs.
