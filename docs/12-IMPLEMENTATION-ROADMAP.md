# 12 — Implementation Roadmap (Task 7: Initial PR Plan)

**No PR below may be created, and no implementation code written, until the product owner approves.**
Target branch for upstream is `preview`; for this fork, PRs go into `custom/main` (confirm).

**Decision (product owner, 2026-11-21): D5 order — Milestones first.** PR sequence is PR 1 Foundation → PR 2 Milestones & timeline → PR 3 Company → PR 4 RBAC → PR 5 Approval engine → PR 6 Timesheet & timer. The table below is kept for reference.

## 1. Order — two candidates

| PR  | `prompt.md` order     | `DECISIONS.md` D5 order (recommended) |
| --- | --------------------- | ------------------------------------- |
| 1   | Foundation & docs     | Foundation & docs                     |
| 2   | Company structure     | **Milestones & timeline**             |
| 3   | Custom RBAC           | Company structure                     |
| 4   | Milestones & timeline | Custom RBAC                           |
| 5   | Timesheet & timer     | **Approval engine**                   |
| 6   | Approval engine       | **Timesheet & timer**                 |

**Recommendation**: approvals before timesheets (timesheet submission depends on the engine, per the module DAG in 03 §11). Whether Milestones go first (D5) or Company first (prompt) is a business-priority call; Company → RBAC are technically ordered (RBAC subjects include departments/teams), Milestones are independent. Either is feasible.

## 2. PR definitions

### PR 1 — Foundation & documentation (already partly on `custom/main`)

- Contains: `plane/custom/*` scaffolding, `plane.custom.core` + health route, two core-line edits, local compose Postgres port → 5435, `docs/DECISIONS.md`, **plus the 15 docs in this pass**.
- Before merge: (pre-existing commit approved by product owner 2026-11-21 ✔); legal sign-off (D6); (`CUSTOM_INSTALLED_APPS` approach decided and implemented in PR 2; CI path filter turned out to need no fix, see 03 R6); health route + registration tests added in PR 2.
- Done when: `manage.py check` clean, `/api/custom/health/` 200, docs reviewed, migration check green.

### PR 2 — Milestones & timeline: backend implemented (branch `feat/pr2-milestones-timeline`, uncommitted)

Models/migration `custom_milestones.0001_initial`, services, permissions, serializers, views, URLs, nightly refresh task, 48 new tests. **Frontend:** route via `routes/extended.ts`, milestones list/timeline page, create/edit/delete, i18n (21 locales), Vitest for `apps/web` — see 08 §9. **Navigation tab added (approved 2026-11-21):** small edits in core `use-navigation-items.ts` (header/tab navigation), `projects-list-item.tsx` (sidebar, via `ProjectNavigation`'s existing `additionalNavigationItems` prop) and `tab-navigation-utils.ts` (so "set as default tab" resolves the right URL), all pointing at `components/milestones/navigation.ts`. `project-navigation.tsx` was deliberately left untouched: it has pre-existing lint warnings that the repo's pre-commit hook (`--deny-warnings`) would attribute to any edit. **Not built:** Gantt markers, work-item linking UI, dependency UI.

### PR 3 — Company organizational structure (Modules 1–2): backend implemented (branch `feat/pr3-company-structure`, stacked on PR 2)

Apps `custom_company` + `custom_teams`, migrations, services, permissions (`plane/custom/core/permissions.py`: workspace ADMIN write, ADMIN/MEMBER read), API, 56 new tests. **Frontend not started.** Original plan follows.

Models `Company, CompanyWorkspace, Department, DepartmentMember, TeamMember`; CRUD APIs; admin UI via route/sidebar seams; Open Q1 (Team) resolved first. Tests: unit + contract + soft-delete cascade.

### PR — Custom RBAC (Module 3)

`PolicyRule/PolicyAssignment`, `PolicyLayer`, check endpoint, settings UI. Blocked on the restrict-only decision (R2) and on departments/teams for subject types.

### (Superseded by PR 2 above) Milestones & timeline (Module 4)

Models, derived status task, timeline read endpoint, Gantt marker spike. Needs Vitest set-up for `apps/web` for frontend tests.

### PR — Approval engine (Module 6)

Generic engine, state machine, adapters registry, inbox UI, expiry task.

### PR — Timesheet & timer (Module 5)

Entries, timer, sweeper, timesheet submit → approval; issue-detail timer widget; "My timesheet" page.

## 3. Cross-cutting per-PR checklist

Copyright headers on every new `.py/.ts/.tsx`; `makemigrations` (lockfile committed); `uv run ruff check`; `pnpm check`; i18n keys in all locales; tests for all new code (AGENTS.md); no core-file edits beyond those approved; docs updated.

## 4. After PR 6

Re-plan modules 7–15 (D5). Likely order: audit (13) → notification center (12) → reporting (7) → workload (8) → documents (11) → risks (9) → automation (10) → OKRs (14) → AI (15). Revisit once real usage informs priorities.

## 5. Recommended first implementation task

Not a feature: **close the PR 1 gates** — approval confirmation of the existing commit, legal review, `CUSTOM_INSTALLED_APPS` decision, CI path-filter fix, and a health-route test. Then start the first feature PR.
