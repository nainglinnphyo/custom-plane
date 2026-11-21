# 02 — Repository Analysis

Everything here was verified by inspecting the checked-out tree (2026-11-21). Items not verified are marked **(unverified)**.

## 1. Baseline

| Item                  | Value                                                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Upstream              | `https://github.com/makeplane/plane` (remote `upstream`)                                                              |
| Fork                  | `https://github.com/nainglinnphyo/custom-plane` (remote `origin`)                                                     |
| Upstream release      | tag `v1.5.0`, commit `18caf808a3` ("release: v1.5.0 #10250")                                                          |
| Current branch / HEAD | `custom/main` @ `26739873ed87d478c003a1fb1cd4235e81066482` (= `v1.5.0` + 1 commit, in sync with `origin/custom/main`) |
| Extra commit          | `2673987` "PR 1: Custom Plane foundation and documentation" (9 files, +263/-1) — see §9                               |
| Working tree          | clean except untracked `prompt.md`                                                                                    |
| Tags                  | 68 present, incl. `v1.4.3-rc1/2`, `v1.5.0-rc1/2`, `v1.5.0`                                                            |
| Branches              | 1 local (`custom/main`); 579 remote-only branches (upstream's)                                                        |
| License               | GNU AGPL-3.0 (`LICENSE.txt`); every source file carries `COPYRIGHT.txt` header (CI-checked)                           |
| Monorepo              | Complete: 5 apps + `proxy`, 14 packages, `deployments/`                                                               |

## 2. Monorepo layout

pnpm workspaces + Turborepo (`pnpm@11.10.0`, Node `>=22.22.0`, `.node-version`=22.22.0). Python backend managed by `uv` (`required-version == 0.12.21`, Python `>=3.12,<3.13`).

| Path           | Role                                                                                                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web`     | Main SPA (React Router framework mode + Vite, MobX stores). Port 3000                                                                                                      |
| `apps/admin`   | Instance admin ("God mode") app. Port 3001                                                                                                                                 |
| `apps/space`   | Public/published boards. Port 3002                                                                                                                                         |
| `apps/live`    | Real-time collaborative editing server (Hocuspocus + Redis extension, HTTP controllers). Port 3100                                                                         |
| `apps/api`     | Django 5.2 + DRF backend (+ Celery workers). Port 8000                                                                                                                     |
| `apps/proxy`   | Caddy reverse-proxy images (`Caddyfile.ce`, `Caddyfile.aio.ce`)                                                                                                            |
| `packages/*`   | `blocks`, `codemods`, `constants`, `decorators`, `editor`, `hooks`, `i18n`, `logger`, `services`, `shared-state`, `tailwind-config`, `types`, `typescript-config`, `utils` |
| `deployments/` | `aio/`, `cli/`, `kubernetes/`, `swarm/` (all under `community/`)                                                                                                           |

UI primitives come from the **published npm package `@makeplane/propel`**; composites live in `@plane/blocks` (subpath imports only). There is no in-repo `packages/ui` or `propel` package.

## 3. Backend (`apps/api/plane`)

### 3.1 Django apps (`INSTALLED_APPS`)

`analytics, app, space, bgtasks, db, utils, web, middleware, license, api, authentication` + (custom) `plane.custom.core`, plus `rest_framework`, `corsheaders`, `django_celery_beat`.

### 3.2 API surfaces (`plane/urls.py`)

| Prefix            | App                    | Auth                                                   | Notes                                                               |
| ----------------- | ---------------------- | ------------------------------------------------------ | ------------------------------------------------------------------- |
| `/api/`           | `plane.app`            | Session cookie (`SessionAuthentication`)               | Internal API for the web/admin SPAs; ~20 url modules, viewset-based |
| `/api/v1/`        | `plane.api`            | API token (`APIKeyAuthentication`, header `X-Api-Key`) | Public REST API; `API_KEY_RATE_LIMIT` default 60/min                |
| `/api/public/`    | `plane.space`          | Anonymous / deploy-board                               | Published boards                                                    |
| `/api/instances/` | `plane.license`        | Mixed                                                  | Instance config / admin                                             |
| `/auth/`          | `plane.authentication` | —                                                      | Email+password, magic code, OAuth (Google, GitHub, GitLab, Gitea)   |
| `/api/custom/`    | `plane.custom.core`    | —                                                      | **Added by PR 1**, health endpoint only                             |

DRF defaults: `SessionAuthentication`, `IsAuthenticated`, JSON renderer, `DjangoFilterBackend`, anon throttle 30/min. OpenAPI via drf-spectacular only when `ENABLE_DRF_SPECTACULAR=1`. Base classes `BaseViewSet` / `BaseAPIView` (`plane/app/views/base.py`) add timezone handling, a read-replica switch (`ReadReplicaControlMixin`, `middleware/db_routing.py`) and `BasePaginator`.

### 3.3 Data layer

- PostgreSQL 15.7 (compose). Read-replica routing middleware exists.
- `BaseModel` (`db/models/base.py`): UUID PK, `created_at/updated_at`, `created_by/updated_by` (auto-filled from `crum.get_current_user()`), **soft delete** (`deleted_at`, `objects` hides deleted, `all_objects` shows). Related soft-delete cascades run in Celery (`soft_delete_related_objects`).
- Hierarchy bases: `WorkspaceBaseModel` (adds `workspace`), `ProjectBaseModel` (adds `project` + `workspace`).
- Uniqueness convention: `unique_together` incl. `deleted_at` **plus** a partial `UniqueConstraint(... condition=deleted_at IS NULL)`.
- ~75 concrete models. Migrations: single `plane.db` app (126 files, latest `0125_reset_project_deploy_board_identity`) + `license` (latest `0006_…`).
- `migrations_lockfile.txt` is rewritten by the repo's overridden `makemigrations` command and **covers every app whose module name starts with `plane.`** — so custom apps will be included automatically.

### 3.4 Domain models relevant to the extension plan

| Concern       | Existing model(s)                                                                                                                  | Key fields                                                                                                                                                                    |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tenant        | `Workspace`                                                                                                                        | slug-routed everywhere                                                                                                                                                        |
| Org members   | `WorkspaceMember`                                                                                                                  | `role` (20/15/5), `company_role` (free text), `is_active`, `*_props` JSON                                                                                                     |
| Teams         | `Team` (`db_table="teams"`)                                                                                                        | `name, description, workspace, logo_props`. **Defined but referenced by no view, serializer or URL** (only model + `0001_initial`) — effectively dormant. No membership table |
| Project       | `Project`, `ProjectMember`, `ProjectIdentifier`                                                                                    | `ProjectMember.role` 20/15/5; `project_lead`, `default_assignee`, `timezone`, feature toggles incl. `is_time_tracking_enabled` (**boolean only — no time entries exist**)     |
| Work item     | `Issue` (+ `IssueType`, `State`, labels, assignees M2M, `IssueRelation`, `IssueComment`, `IssueLink`, `IssueAttachment`, versions) | `start_date`, `target_date` (DateField), `estimate_point`, `priority`, `parent`, `completed_at`, `type`                                                                       |
| Dependencies  | `IssueRelation`                                                                                                                    | `relation_type` with forward/reverse pairs (`IssueRelationChoices._RELATION_PAIRS`)                                                                                           |
| Time-boxes    | `Cycle` (start/end DateTime, `owned_by`, `progress_snapshot`, timezone), `Module` (start/target Date, `status`, `lead`, members)   |                                                                                                                                                                               |
| Views         | `IssueView` (workspace-scoped saved filters, `rich_filters`)                                                                       |                                                                                                                                                                               |
| Docs          | `Page` (+ `ProjectPage`, `PageVersion`, `PageLog`, `PageLabel`)                                                                    | rich text with binary Yjs description                                                                                                                                         |
| History/audit | `IssueActivity` (verb, field, old/new value, actor, epoch), `IssueVersion`, `APIActivityLog`, `WebhookLog`, `EmailNotificationLog` | Written by Celery task `issue_activity` (**88 call sites**)                                                                                                                   |
| Notifications | `Notification`, `UserNotificationPreference`, `EmailNotificationLog`                                                               | read/snooze/archive                                                                                                                                                           |
| Files         | `FileAsset`                                                                                                                        | S3-compatible                                                                                                                                                                 |
| Webhooks      | `Webhook`, `ProjectWebhook`, `WebhookLog`                                                                                          | `MODEL_MAPPER`: project, issue, cycle, module, cycle_issue, module_issue, issue_comment, user, intake_issue                                                                   |
| Approvals     | **none** (grep finds no approval concept in `plane/`)                                                                              | —                                                                                                                                                                             |

### 3.5 Authorization (two divergent layers)

- `plane/app/permissions/` — DRF permission classes (`WorkSpaceBasePermission`, `WorkSpaceAdminPermission`, `ProjectBasePermission`, …) and the `@allow_permission(allowed_roles, level="PROJECT"|"WORKSPACE", creator, model)` decorator. **Imported by 69 modules.**
- `plane/utils/permissions/` — a parallel copy of `ROLE` + `allow_permission` + project/workspace/page classes. **Imported by 3 modules.**
- `ROLE` enum: `ADMIN=20, MEMBER=15, GUEST=5`; also `ROLE_CHOICES` on models. `ROLE` appears ~364 times across `plane/` — it is deeply structural. (`DECISIONS.md` D3 says "7 hard-coded locations"; that figure was not reproducible — see §9.)
- No object-level / permission-table mechanism; roles are per-workspace and per-project integers.

### 3.6 Background processing

Celery + RabbitMQ broker (`CELERY_BROKER_URL`), Redis/Valkey present for caching/sessions-adjacent use **(exact usage unverified)**, `django_celery_beat`. `plane/celery.py` defines the beat schedule (email stacking every 5 min, intake unsnooze, auto-archive/close, hard-delete, S3 link cleanup, log cleanup, page/issue version cleanup, telemetry). 33 task modules in `plane/bgtasks/` (notably `issue_activities_task.py` 52 KB, `notification_task.py` 33 KB, `webhook_task.py`, `email_notification_task.py`, `export_task.py`).

### 3.7 Real-time

`apps/live`: Hocuspocus (Yjs) for collaborative **page/document editing** with Redis + database extensions and HTTP controllers (collaboration, document, health, pdf-export). There is **no general event bus / websocket push for notifications or board updates** in the tree; UI updates come from REST + MobX.

### 3.8 File storage

`django-storages` S3 backend; MinIO-compatible (`USE_MINIO`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_BUCKET_NAME`); local compose uses the `pgsty/silo` MinIO image. Uploads are tracked by `FileAsset` (upload mechanism details unverified).

### 3.9 Tests

`pytest` + `pytest-django` (`pytest.ini`: markers `unit`, `contract`, `smoke`, `slow`; `--nomigrations --reuse-db`), tests under `apps/api/plane/tests/{unit,contract,smoke}`. Run in Docker via `docker-compose-test.yml`. Frontend: Vitest in `apps/live`, `packages/{blocks,codemods,editor,services}`; **`apps/web`, `apps/admin`, `apps/space` have no test script.**

## 4. Frontend

- `apps/web`: React Router (framework mode, `app/routes.ts` = `coreRoutes` + `extendedRoutes`), MobX stores in `apps/web/store/*` (`issue`, `cycle`, `module`, `timeline`, `member`, `notifications`, `pages`, `workspace`, `project`, …), components in `apps/web/components/*` (`gantt-chart`, `workflow`, `base-layouts`, `issues`, `modules`, `cycles`, `views`, `workspace-notifications`, `analytics`, `automation`, …), service layer `apps/web/services` + `@plane/services`.
- Gantt/timeline already exists (`components/gantt-chart`, `store/timeline`, `packages/types/src/base-layouts/gantt`). Layouts: gantt, kanban, list (and others in issue layouts).
- i18n: `packages/i18n/src/locales/<lang>/*.json`; `en` is source of truth, all locales must share keys (CI `sync:check`).

### 4.1 Frontend extension seams

27 tracked files have `extended` in their path (counted by `git ls-files | grep -ci extended`). Verified examples:

- `apps/web/app/routes/extended.ts` (empty route list merged with core routes)
- `apps/web/components/workspace/sidebar/extended-sidebar-item.tsx`, `app/(all)/[workspaceSlug]/(projects)/extended-sidebar*.tsx`, `components/common/extended-app-header.tsx`
- `apps/web/hooks/{use-workspace-issue-properties-extended,editor/use-extended-editor-config,pages/use-extended-editor-extensions,oauth/extended}`, `store/pages/extended-base-page.ts`
- `packages/types/src/base-layouts/gantt/extended.ts`, `packages/types/src/page/extended.ts`, `packages/types/src/rich-filters/**/extended.ts`, `packages/constants/src/{auth,rich-filters/operator-labels}/extended.ts`
- `apps/admin/{providers/extended.tsx,components/common/header/extended.ts}`, `apps/space/hooks/oauth/extended.tsx`, `apps/live/src/services/page/extended.service.ts`
- **Backend: exactly one** — `apps/api/plane/utils/instance_config_variables/extended.py`.

**Correction (PR 2 frontend work):** the `extended` name is _not_ a reliable marker of a no-op seam. Several of these files are real, working UI — e.g. `extended-sidebar.tsx`, `extended-project-sidebar.tsx`, `extended-sidebar-wrapper.tsx`, `extended-sidebar-item.tsx` implement the "extended" (pinned/expanded) sidebar panel and `extended-app-header.tsx` is the app header wrapper. They must not be treated as extension points. The verified empty/no-op seams are: `app/routes/extended.ts` (now used by PR 2), `packages/types/src/base-layouts/gantt/extended.ts`, `packages/constants/src/{auth,rich-filters/operator-labels}/extended.ts`, `packages/types/src/{page,rich-filters/*}/extended.ts`, and the OAuth/provider hooks. **There is no seam for project navigation tabs**: `components/navigation/use-navigation-items.ts` and `components/workspace/sidebar/project-navigation.tsx` are core files, so adding a "Milestones" tab needs a small edit to both (see 12 PR 2).

The original statement follows. These were described as intended upstream no-op hook points. Their _stability_ across releases was asserted in `DECISIONS.md` D4 (seam files unchanged across `v1.4.3..v1.5.0`) but **was not re-verified in this pass** (unverified).

## 5. Infrastructure & deployment

| Artifact                           | Contents                                                                                                                                                                       |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `docker-compose-local.yml`         | plane-redis (valkey 7.2), plane-mq (rabbitmq 3.13), plane-minio (silo), plane-db (postgres 15.7), api, worker, beat-worker, migrator. Frontends run via `pnpm dev` on the host |
| `docker-compose.yml`               | Production-shape: web, admin, space, api, worker, beat-worker, migrator, live, plane-db, plane-redis, plane-mq, plane-minio, proxy (built from repo Dockerfiles)               |
| `docker-compose-test.yml`          | Isolated backend test stack                                                                                                                                                    |
| `deployments/cli/community`        | `install.sh`, `docker-compose.yml` (registry images), backup/restore scripts                                                                                                   |
| `deployments/aio/community`        | All-in-one single-image (supervisor)                                                                                                                                           |
| `deployments/swarm/community`      | `swarm.sh`                                                                                                                                                                     |
| `deployments/kubernetes/community` | **README only** → external Helm chart `makeplane/plane-ce` at `helm.plane.so`. No manifests in the repo                                                                        |
| CI                                 | `.github/workflows/*` incl. `migration-check.yml`, copyright check, i18n sync                                                                                                  |

## 6. Dev environment status (this machine)

See `docs/13-DEPLOYMENT-GUIDE.md` §2 for the full table. Summary: backend stack was already running and healthy; frontend dev servers **cannot start** on default ports (3000–3002, 3100 are held by unrelated projects).

## 7. Reuse map (feature → what exists)

| Proposed module         | Plane provides                                                                                  | Verdict                                                     |
| ----------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 1 Company/departments   | `Workspace`; `WorkspaceMember.company_role` (text)                                              | Nothing for hierarchy — build                               |
| 2 Teams/memberships     | Dormant `Team` model (no members, no API)                                                       | Extend/replace — decision needed (§03 open Q)               |
| 3 Custom RBAC           | 3-value `ROLE` at workspace+project level                                                       | Build as restrict-only layer                                |
| 4 Milestones/timeline   | `Module`, `Cycle`, `IssueRelation`, Gantt UI                                                    | Partial reuse; no milestone entity                          |
| 5 Timesheets/timer      | `Project.is_time_tracking_enabled` flag only                                                    | Full build                                                  |
| 6 Approvals             | none                                                                                            | Full build                                                  |
| 7 Reporting             | `plane.analytics`, `AnalyticView`, export tasks, saved views                                    | Extend                                                      |
| 8 Workload              | Estimates, assignees, cycles                                                                    | Mostly build                                                |
| 9 Risks                 | none (could model as a work-item type)                                                          | Build                                                       |
| 10 Recurring/automation | auto-archive/close tasks; `workflow` stub component                                             | Build                                                       |
| 11 Documents            | `Page` + versions + live collab + `FileAsset`                                                   | Mostly reuse                                                |
| 12 Notification center  | `Notification`, preferences, email stacking                                                     | Extend                                                      |
| 13 Audit logs           | `IssueActivity` (issue-only), `APIActivityLog`                                                  | Extend — no workspace-wide audit                            |
| 14 OKRs                 | none                                                                                            | Full build                                                  |
| 15 AI assistant         | LLM provider registry (OpenAI/Anthropic/Gemini) + instance `LLM_*` config, text-completion only | Reuse provider layer; assistant/tools/conversations are new |

## 7a. Upstream already anticipates a Milestones feature (found in PR 2)

Plane v1.5.0 ships _placeholders_ for a Milestones feature whose implementation is not in this repository (it appears to belong to a paid edition): i18n strings `common.milestones`, `common.milestones_description`, `project-settings` feature toggle "Enable milestones", the `PROJECT_MILESTONES` fetch key (`packages/constants/src/fetch-keys.ts`), a `milestone` empty-state illustration in `@plane/blocks`, and `"milestones"` in the project overview collapsible sections. The custom module reuses these (fetch key, translation strings, naming) rather than redefining them. **Risk:** if a future upstream CE release implements Milestones, routes/strings/UI will overlap with ours — re-check on every upstream sync (15 §3).

## 8. Findings that affect design

1. Two permission modules with duplicated `ROLE` (69 vs 3 importers) — wrap `plane.app.permissions`, do not touch either.
2. `Team` is dormant — naming collision/reuse question for module 2.
3. `IssueActivity` only covers work items; every custom audit/event must be written by custom code.
4. CI `migration-check.yml` path filters (`plane/*/migrations/*.py`, `apps/api/*/migrations/*.py`) are git pathspecs whose `*` crosses `/`, so they **do** match `plane/custom/<mod>/migrations/*.py` (verified with `git ls-files` in PR 2). Only the cosmetic `🔄migrations` PR-label grep (`^apps/api/plane/[^/]*/migrations/0…`) misses nested custom apps.
5. `custom.core` uses `BigAutoField`; Plane's own models use UUID PKs via `BaseModel`. Custom business models should inherit `WorkspaceBaseModel`/`BaseModel`.

## 9. State of the pre-existing "PR 1" commit

The repository already contained commit `2673987` before this pass. It:

- added `plane/custom/<15 modules>/` directories (most empty) and the `plane.custom.core` app with a health route,
- edited **two core files** (`settings/common.py` +2 lines, `urls.py` +2 lines),
- changed `docker-compose-local.yml` Postgres host port to `5435`,
- added `docs/DECISIONS.md` marked "Approved for implementation".

`prompt.md` says implementation code must not change without approval. I did **not** revert or alter that commit. **The product owner confirmed (2026-11-21) that this commit was approved.** Two claims in `DECISIONS.md` were checked: "26 frontend seams" → 27 `extended` files found (consistent); "ROLE in 7 locations" → not reproducible (364 references).
