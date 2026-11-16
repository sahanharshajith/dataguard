# Development guide

## Workflow (GitHub Flow, one pull request per phase)

1. Start from an up-to-date `main`:
   ```bash
   git switch main && git pull --ff-only
   git switch -c feature/<topic>
   ```
2. Commit small, meaningful steps with Conventional Commit messages (`feat(scope): ...`, `fix`, `docs`, `test`, `chore`, `ci`).
3. Push the branch regularly. Open the pull request when the phase checklist is complete.
4. Wait for the CI checks, review your own diff, and merge with **Create a merge commit** so the step-by-step history is kept.
5. Delete the branch and sync: `git switch main && git pull --ff-only && git branch -d feature/<topic>`.

Never commit to `main` directly, never force-push it, and never commit `.env`.

## Everyday commands

| Task | Command |
|---|---|
| Start the stack | `docker compose up -d --build` |
| Stop it | `docker compose down` (add `-v` to also delete data) |
| Apply migrations | `docker compose exec backend alembic upgrade head` |
| New migration after a model change | `docker compose exec backend alembic revision --autogenerate -m "message"`, then **review the file** |
| Unit tests | `pytest` |
| Unit + integration tests | set `TEST_DATABASE_URL` (see README), then `pytest` |
| Frontend lint and build | `docker compose run --rm --no-deps frontend sh -c "npm run lint && npm run build"` |

## Rules of the codebase

- Database rules (constraints, defaults, cascades) live in PostgreSQL, and integration tests prove they hold.
- Every model change comes with an Alembic migration; CI fails if the two disagree.
- Allowed values for fixed-choice columns are defined once, in `backend/app/models/enums.py`.