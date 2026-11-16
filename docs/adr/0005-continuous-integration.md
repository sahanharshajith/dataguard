# ADR 0005: Continuous integration with GitHub Actions

- **Status:** Accepted
- **Date:** 2026-11-16

## Context
The project has unit tests, integration tests against PostgreSQL, Alembic migrations, and a Docker Compose stack. Without automation, a change can pass on one machine and break another, and the migrations can drift from the models unnoticed.

## Decision
Use GitHub Actions. Every pull request and every push to `main` runs three parallel jobs:
1. Backend tests: all unit and integration tests against a PostgreSQL service container.
2. Docker Compose smoke test: validate the Compose file, build the images, start PostgreSQL and the backend, apply migrations, call `/health/db`.
3. Frontend: install, lint, and production build (type check).

Dependabot proposes updates to GitHub Actions, npm packages, Dockerfiles, and Compose images.

## Consequences
- Regressions, including model/migration drift, are caught before merge.
- Airflow is not started in CI because its image is large; DAG tests are added in Phase 10.
- Python dependencies use version ranges, so a new upstream release can break CI without any change from us. That is acceptable for now, and pinning is planned for Phase 11b.
- Continuous delivery (publishing images) is deferred until production images exist.