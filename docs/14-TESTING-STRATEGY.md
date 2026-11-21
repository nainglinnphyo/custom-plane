# 14 — Testing Strategy

## 1. Existing infrastructure (verified)

| Layer         | Tooling                                                                                                                                                                                                                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend       | `pytest` + `pytest-django`; `apps/api/pytest.ini` (markers `unit`, `contract`, `smoke`, `slow`; `--strict-markers --reuse-db --nomigrations`); suites in `plane/tests/{unit,contract,smoke}` with `conftest.py` and `factories.py`; guides `plane/tests/TESTING_GUIDE.md`, `apps/api/tests/RUNNING_TESTS.md` |
| Runner        | Docker: `docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests`; subset: `… run --rm --build api-tests pytest -m unit`                                                                                                                                   |
| Frontend      | Vitest in `apps/live`, `packages/{blocks,codemods,editor,services}`. **None** in `apps/web`, `apps/admin`, `apps/space`                                                                                                                                                                                      |
| Static checks | `pnpm check` (oxfmt, OxLint, tsc), `ruff` (`apps/api/ruff.toml`), i18n sync check                                                                                                                                                                                                                            |
| CI            | `pull-request-build-lint-api.yml`, `…-web-apps.yml`, `migration-check.yml`, `copyright-check.yml`, `i18n-sync-check.yml`, `codeql.yml`                                                                                                                                                                       |

Note `--nomigrations`: tests build the schema from models, so **migration correctness is not exercised by pytest** — rely on `makemigrations --check` and a migrate-on-fresh-DB CI step for custom apps.

## 2. Rules for custom code (per AGENTS.md: "All features require unit tests")

1. Every custom module has `plane/tests/unit/custom/<module>/` and `plane/tests/contract/custom/<module>/`.
2. Permission matrix test per endpoint (Admin / Member / Guest / non-member / other workspace).
3. State machines (approvals, timesheets, milestone status) get exhaustive transition tests.
4. Service-layer tests for cross-module calls; no module tests another's private models.
5. Concurrency tests (double timer start, double approve) using transactions.
6. Time-sensitive logic uses frozen time and timezone cases (DST).
7. Celery tasks tested synchronously (`CELERY_TASK_ALWAYS_EAGER` or direct call) — confirm the existing pattern in `conftest.py` before PR 2.
8. A regression test that core behavior is unchanged: `/api/instances/` and a representative core endpoint still respond.
9. Frontend: add Vitest (+ jsdom/Testing Library) to `apps/web` for custom components/stores in the first frontend PR; shared logic in `packages/*` uses existing Vitest projects.

## 3. Gates before merge

`ruff check`, `uv run python manage.py check`, `makemigrations --check --dry-run`, backend suite in Docker, `pnpm check`, i18n sync, copyright check, and — for upstream syncs — the **full** backend suite plus a UAT compose smoke test.

## 4. Baseline not yet established

The full upstream backend suite was **not run** in this pass (long-running; needs the test stack). Run it once on the clean `v1.5.0` + PR 1 baseline and record the result before PR 2 so later failures can be attributed.
