# 08 — Milestone & Timeline Design (PROPOSED)

## 1. What Plane already has (verified)

| Capability           | Where                                                                                                                                                                       |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Work-item dates      | `Issue.start_date`, `Issue.target_date` (DateField)                                                                                                                         |
| Dependencies         | `IssueRelation.relation_type` ∈ `blocked_by`, `start_before`, `finish_before`, `relates_to`, `duplicate`, `implemented_by` (+ reverse pairs)                                |
| Time-boxed groupings | `Cycle` (start/end DateTime, timezone, progress snapshot), `Module` (start/target Date, `status`, lead, members)                                                            |
| Timeline UI          | `apps/web/components/gantt-chart`, `apps/web/store/timeline`, `packages/types/src/base-layouts/gantt/` incl. empty seam `extended.ts` (`EXTENDED_GANTT_TIMELINE_TYPE = {}`) |
| Saved views          | `IssueView` (workspace)                                                                                                                                                     |

There is **no milestone entity**. `Module` is a feature grouping with its own status/UI; reusing it as a milestone would couple custom behavior to an upstream model that changes between releases.

## 2. Design

- New `Milestone`, `MilestoneIssue`, `MilestoneDependency` (see 04 §4), project-scoped.
- **Derived status** (`planned / in_progress / achieved / missed`) computed from linked work items' `State.group` (existing grouping) and `due_date`; stored value refreshed by a Celery task and on link changes. Manual override allowed only by project Admin.
- **Timeline feed**: `GET …/projects/<pid>/timeline/` returns milestones (+ their dependencies) as a read model so the existing Gantt can render them as markers/bars without changing core Gantt endpoints.
- Dependencies between milestones: finish-to-start only in v1; cycle detection on write.
- Date sanity: a milestone's due date is not auto-moved by work-item date edits; instead a "at risk" flag is derived when linked items' `target_date` exceeds `due_date`.

## 3. Frontend integration

- Route and sidebar entry via `apps/web/app/routes/extended.ts` and `extended-sidebar-item.tsx`.
- Gantt: extend the `extended.ts` type seam in `packages/types/.../gantt/` and render milestone markers from a custom block component. **Needs a spike**: how `components/gantt-chart` accepts extra block types has not been read in depth (unverified).
- MobX store in `apps/web/store/` (custom file) + service in `@plane/services` pattern.
- i18n: all strings added to every locale (`pnpm --filter=@plane/i18n sync:check`).

## 4. Authorization

Project MEMBER/ADMIN create & edit, GUEST read (respecting `guest_view_all_features`), plus policy layer.

## 5. Background

`refresh_milestone_status` (on change + nightly beat).

## 6. Testing

Status derivation table tests, dependency-cycle tests, permission tests, query-count test for the timeline endpoint; frontend component tests need Vitest set up in `apps/web` (currently none).

## 7. Upstream conflict risk

Backend: low (new app). Frontend Gantt: medium — depends on upstream Gantt internals; mitigated by confining changes to seam files and a separate custom component dir.

## 8. Implementation status (PR 2, backend)

Implemented in `apps/api/plane/custom/milestones/` (app label `custom_milestones`, tables `custom_milestones`, `custom_milestone_issues`, `custom_milestone_dependencies`; migration `0001_initial`).

- **Status is computed, not trusted.** API responses derive status from annotated work-item counts in one query (`services.annotate_progress` / `effective_status`); the stored `status` is a cache refreshed on writes and by the nightly beat task `custom-milestones-refresh-statuses` (04:00 UTC). A project admin can set a manual override (`status_override`) by PATCHing `status`; `null` clears it.
- **Rules** (`services.derive_status`): no items → planned; ≥1 completed and all items completed/cancelled → achieved; else due date passed → missed; else any started/completed → in_progress; else planned. Archived, draft, triage and soft-deleted work items are ignored.
- **At risk**: not achieved and some open linked item has `target_date` after the milestone's `due_date`.
- **Dependencies**: finish-to-start only; self, duplicate, cross-project and (transitive) cycles are rejected.
- **Tenant safety**: every lookup is scoped by workspace slug + project id; linking issues validates they belong to the milestone's project; foreign ids return 400/404 and nothing is written.
- **Frontend: implemented (see §9).** **Not done yet**: Gantt integration, work-item linking UI, dependency UI; deleted milestones' links/dependencies rely on the core soft-delete cascade task (covered by the model default manager, not separately tested); list endpoints are unpaginated by design (milestones per project are few).

## 9. Implementation status (PR 2, frontend)

Route `/:workspaceSlug/projects/:projectId/milestones`, registered through the empty `apps/web/app/routes/extended.ts` seam. It mirrors the core layout chain so `mergeRoutes` nests it inside the project layout (verified in a running dev server).

- `apps/web/components/milestones/` — `root` (SWR via the upstream `PROJECT_MILESTONES` fetch key), `list` (rows with status/at-risk badges, progress bar and a shared date-axis timeline with a "today" marker), `form`/`modal` (create/edit, mirrors the Cycle form), `delete-modal`, pure `helpers` (timeline math, unit-tested), `types`.
- `apps/web/services/milestone.service.ts` — client for `/api/custom/…`.
- i18n: new namespace `milestone` (12 keys) translated for all 21 non-English locales; everything else reuses existing keys (`common.planned/in_progress/completed/at_risk`, `module.details_drawer.progress.done`, `milestones`). Translations were authored against the skill's glossary and **need native review**. `@plane/i18n` must be rebuilt (`pnpm --filter @plane/i18n build`) for dev servers to see a new namespace.
- Tests: `apps/web` now has Vitest (`pnpm --filter web test`, `vitest.config.ts`, devDependency + lockfile entry); 10 helper tests.
- Verified in a browser (dev server on :3010 against the Docker API): empty state, create, edit prefill, delete + toast, status / at-risk / progress / timeline rendering for seeded data.
- **Not done:** Gantt-chart integration (a standalone timeline avoids touching upstream Gantt internals), work-item linking UI (API exists), dependency UI, component-level tests (no jsdom/Testing Library set up), narrow-viewport and RTL checks.
- Navigation: "Milestones" tab in the project sidebar, header tabs and tab-navigation (verified in the sidebar in a browser).
