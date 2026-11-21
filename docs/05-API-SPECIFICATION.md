# 05 — API Specification (PROPOSED)

## 1. Existing API conventions (verified)

- Internal session-cookie API at `/api/` (viewsets in `plane/app/views`, URLs in `plane/app/urls/*.py`); public token API at `/api/v1/` (`X-Api-Key`, 60/min default); published boards `/api/public/`.
- Workspace-scoped paths use `workspaces/<slug>/…`; project-scoped `workspaces/<slug>/projects/<project_id>/…`.
- Base classes: `BaseViewSet` (ModelViewSet) / `BaseAPIView` with timezone mixin, read-replica control, `BasePaginator`; default `IsAuthenticated`; permission via `@allow_permission(...)` on methods.
- JSON only; DRF `DjangoFilterBackend`; errors via `auth_exception_handler`.
- OpenAPI available only with `ENABLE_DRF_SPECTACULAR=1`.

## 2. Custom API conventions

- Mounted at `/api/custom/` (already present). Each module adds one `path("<module>/", include(...))` in `plane/custom/core/urls.py`.
- Session auth, same CSRF/cookie model as `/api/`. No API-token variant in PRs 2–6.
- Reuse `BaseViewSet` / `BaseAPIView`; decorate with core `@allow_permission` first, then the custom policy decorator (see 06).
- Pagination: the existing `BasePaginator` cursor style (match core list endpoints).
- Errors: DRF default shapes `{"error": "..."}` consistent with core; 403 for permission, 404 when the object is outside the caller's workspace/project (do not leak existence).
- Never accept `workspace`/`project` in the body for scoping — derive from the URL and verify membership.

## 3. Endpoint plan

Health (exists): `GET /api/custom/health/` → `{"status":"OK","service":"custom-plane"}` (currently unauthenticated; verified returns 200).

| Module                    | Method + path                                                                                                                                                                                                                                                                                                                                                                           | Purpose                    | Min. role                                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Company                   | _removed_                                                                                                                                                                                                                                                                                                                                                                               | —                          | Dropped in D9: a workspace is the company; split companies = split workspaces                              |
| Departments ✅            | `GET/POST /workspaces/<slug>/departments/`, `GET/PATCH/DELETE …/<id>/` (delete refused while sub-departments exist), `GET/POST …/<id>/members/`, `PATCH/DELETE …/<id>/members/<user_id>/`                                                                                                                                                                                               | hierarchy & membership     | workspace ADMIN write, ADMIN/MEMBER read; guests denied                                                    |
| Teams ✅                  | `GET/POST /workspaces/<slug>/teams/`, `GET/PATCH/DELETE …/<id>/`, `GET/POST …/<id>/members/`, `PATCH/DELETE …/<id>/members/<user_id>/`                                                                                                                                                                                                                                                  | teams                      | workspace ADMIN write, ADMIN/MEMBER read; guests denied                                                    |
| RBAC                      | `GET/POST /workspaces/<slug>/rbac/rules/`, `…/assignments/`, `POST /rbac/check/` (dry-run)                                                                                                                                                                                                                                                                                              | policy admin               | ADMIN                                                                                                      |
| Milestones ✅ implemented | `GET/POST /workspaces/<slug>/projects/<pid>/milestones/`; `GET/PATCH/DELETE …/milestones/<id>/` (no PUT); `GET/POST …/milestones/<id>/issues/` (body `{issue_ids:[…]}`, max 500) and `DELETE …/issues/<issue_id>/`; `POST …/milestones/<id>/dependencies/` (body `{depends_on}`) and `DELETE …/dependencies/<dep_id>/`; `GET …/projects/<pid>/timeline/` → `{milestones, dependencies}` | milestones + timeline feed | project MEMBER/ADMIN write; GUEST read only if `guest_view_all_features`; `status` override: project ADMIN |
| Timer                     | `POST /workspaces/<slug>/time/timer/start/`, `POST …/stop/`, `GET …/active/`                                                                                                                                                                                                                                                                                                            | timer                      | MEMBER                                                                                                     |
| Entries                   | `GET/POST /workspaces/<slug>/time/entries/`, `PATCH/DELETE …/<id>/`                                                                                                                                                                                                                                                                                                                     | time entries               | owner (+ADMIN read)                                                                                        |
| Timesheets                | `GET/POST /workspaces/<slug>/time/timesheets/`, `POST …/<id>/submit/`, `GET …/<id>/`                                                                                                                                                                                                                                                                                                    | periods                    | owner                                                                                                      |
| Approvals                 | `GET /workspaces/<slug>/approvals/inbox/`, `GET …/<id>/`, `POST …/<id>/approve/`, `…/reject/`, `GET/POST /approvals/flows/`                                                                                                                                                                                                                                                             | engine                     | step approver / ADMIN                                                                                      |

Payload schemas are intentionally not written here; they will be produced per module with the serializers and checked into the OpenAPI schema when each PR is approved.

## 4. Versioning & compatibility

- Custom API is versionless under `/api/custom/` until a second consumer exists; breaking changes require a new prefix.
- Do not add fields to core endpoints. If the UI needs custom data on a work item, call a custom endpoint (batch by issue ids) rather than extending core serializers.

## 5. Testing

Contract tests under `apps/api/plane/tests/contract/custom/` using the existing `pytest` fixtures (`conftest.py`, factories); see 14.
