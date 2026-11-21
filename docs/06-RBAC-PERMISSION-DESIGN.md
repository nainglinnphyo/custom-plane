# 06 — RBAC & Permission Design (PROPOSED)

## 1. Existing mechanisms (verified)

- **Roles** are integers: `ADMIN=20`, `MEMBER=15`, `GUEST=5` on `WorkspaceMember.role` and `ProjectMember.role`.
- **Authentication**: session cookie (DB-backed session model), OAuth (Google/GitHub/GitLab/Gitea), email/password, magic code; `/api/v1` API tokens.
- **Authorization** (two parallel modules):
  - `plane/app/permissions/` — DRF classes + `@allow_permission(allowed_roles, level, creator, model)`; used by **69** modules.
  - `plane/utils/permissions/` — duplicated `ROLE` / `allow_permission`; used by **3** modules.
- `allow_permission` resolves workspace slug / project id from URL kwargs, checks active membership and role; with `creator=True, model=…` also lets an object's creator through.
- No object-level ACLs, no permission tables, no custom roles. ~364 references to `ROLE` across the backend → roles are structural.

## 2. Requirement gap

The brief asks for "Custom RBAC". The only approach that keeps upstream merges clean (D3) is a **restrict-only** layer. That means:

- ✅ Can: deny actions/resources to users, departments, teams or roles; scope denies to a project.
- ❌ Cannot: give someone _more_ than their Admin/Member/Guest allows (e.g. a "Finance viewer" who can read a project they're not a member of).

**Product-owner decision required** (R2 in 03).

## 3. Design

```
request ──► core @allow_permission (role check)  ──► custom PolicyLayer.check()
                 │ 403 if core denies                    │ deny rule matches? → 403
                 ▼                                       ▼ else → proceed
```

- `PolicyLayer.check(user, action, resource, context) -> bool | None` — returns `False` (deny) or `None` (defer to core). It **never returns allow-over-core**.
- Rules (`PolicyRule`) evaluated by priority; any matching deny wins. Subjects: user, department, team, or core role value. Scope: workspace or project.
- Action vocabulary is a closed enum in `plane/custom/rbac/actions.py` (e.g. `custom.timesheet.approve`, `custom.milestone.edit`). **Core actions are not hooked in this phase** — hooking core views would require editing them. Custom endpoints call the layer explicitly.
- Cache: per-user resolved deny-set in Redis, invalidated on rule/membership change (Celery task).
- Admin UI: workspace settings page registered through `routes/extended.ts`.

## 4. Module-level rules (apply to all custom endpoints)

1. Authenticate; resolve workspace by slug; require **active** `WorkspaceMember`.
2. Project-scoped: require active `ProjectMember` (guests read-only) — via the existing core decorator.
3. Ownership: users edit only their own timers/entries/timesheets unless Admin.
4. Policy layer may further deny.
5. All denials logged to the audit module once it exists (until then, standard logger).

## 5. Security considerations

- Authorization in services as well as views so Celery tasks and the AI module cannot bypass checks.
- The AI assistant (module 15) must run with the **requesting user's** permissions, never a service account.
- The health endpoint is unauthenticated; keep it free of version/config data.
- `GET /api/custom/*` must not leak cross-workspace existence (return 404).

## 6. Tests

Matrix test: {Admin, Member, Guest, non-member} × {allowed, denied-by-policy} × {workspace, project scope}; regression test asserting the policy layer can never turn a core 403 into a 200.
