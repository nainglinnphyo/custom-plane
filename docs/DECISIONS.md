# Custom Plane — Architecture Decisions

**Status**: Approved for implementation  
**Date**: 2026-11-19  
**Baseline**: v1.5.0 (commit `18caf808a3`)

---

## D1 — Where Custom Code Lives

**Decision**: New Django apps under `plane/custom/<module>/` with **additive migrations only** (no `ALTER` on core tables). Frontend code uses the 26 upstream extension seams exclusively.

**Rationale**:

- Backend has only **one seam** (`plane/utils/instance_config_variables/extended.py`) — registering a custom app requires two unavoidable core edits: one line in `INSTALLED_APPS` (`settings/common.py`) and one `path(...)` in `plane/urls.py`
- Frontend is well-covered with 26 purpose-built no-op extension points (empty arrays, pass-through components) — near-zero merge conflict
- Custom apps get their own `migrations_lockfile.txt` line → low conflict surface

**Implementation**:

```
plane/
├── custom/
│   ├── company/          # Module 1: Company & departments
│   ├── teams/            # Module 2: Teams & memberships
│   ├── rbac/             # Module 3: Custom RBAC
│   ├── milestones/       # Module 4: Milestones & timeline
│   ├── timesheets/       # Module 5: Timesheets & timer
│   ├── approvals/        # Module 6: Approval workflow
│   ├── reporting/        # Module 7: Advanced reporting
│   ├── workload/         # Module 8: Resource & workload planning
│   ├── risks/            # Module 9: Project risk management
│   ├── automation/       # Module 10: Recurring tasks & automation
│   ├── documents/        # Module 11: Document management
│   ├── notifications/    # Module 12: Notification center
│   ├── audit/            # Module 13: Audit logs
│   ├── okrs/             # Module 14: Company OKRs
│   └── ai/               # Module 15: AI assistant
```

---

## D2 — Company/Department Tier

**Decision**: **Option (a) + (b)** — `Company` as a grouping _alongside_ workspaces (for reporting rollups only); `Department` as a workspace-scoped entity. **NOT option (c)** — no true tier above Workspace.

**Rationale**:

- Plane is workspace-rooted end-to-end (slug in every route, every permission check)
- Option (c) touches the permission layer and every URL — highest architectural risk
- Option (a) + (b) uses existing Workspace as the tenant boundary; Company/Department are additive reporting/grouping layers
- Departments can be modeled as `Workspace`-scoped entities with a `department_type` field

**Implementation**:

- `Company` model: `name`, `slug`, `settings` (JSON), `created_at` — no FK to Workspace
- `CompanyWorkspace` join: `company`, `workspace`, `is_primary` — for rollup queries
- `Department` model: `workspace` (FK), `name`, `description`, `parent_department` (self-FK for hierarchy), `members` (M2M via `DepartmentMember`)

---

## D3 — RBAC Strategy

**Decision**: **Additive policy layer** evaluated _after_ the core `@allow_permission` check, able **only to further restrict** — never to grant above the user's `ROLE` (20/15/5).

**Rationale**:

- `ROLE` enum is structural (7 hard-coded locations); dynamic roles would require touching hundreds of call sites
- Two divergent permission layers exist (`plane/app/permissions/` vs `plane/utils/permissions/`) — a restrict-only wrapper keeps both intact
- Upstream merges stay clean: core permission checks unchanged

**Implementation**:

```python
# plane/custom/rbac/policies.py
class PolicyLayer:
    """Evaluated AFTER allow_permission() — only restricts, never grants."""

    @staticmethod
    def check(user, action, resource, context):
        # Returns: True (allow), False (deny), None (defer to core)
        pass

# Applied via middleware or decorator wrapper:
@allow_permission(allowed_roles=[ADMIN, MEMBER])
@policy_restrict(action="issue.delete", resource="Issue")
def delete_issue(request, issue_id): ...
```

---

## D4 — Upstream Sync Model

**Decision**: **Long-lived custom trunk** (`custom/main`) branching from release **tags**, merging `vX.Y.Z` tags only.

**Process**:

1. `git fetch upstream --tags`
2. `git merge vX.Y.Z` (release tag, never `preview`)
3. Resolve conflicts in custom-owned files only
4. Gate on: full backend suite + UAT compose deployment
5. Rehearse on RC tags (`vX.Y.Z-rcN`)

**Rationale**:

- Upstream cadence: release every 4–8 weeks, 1–3 RC tags beforehand
- `preview` is the default branch (where PRs land), `master` is stale — tags are stable sync points
- Seam strategy empirically validated: across `v1.4.3..v1.5.0` (192 commits, 4,465 files), seam files were **unchanged** while every core file custom code must edit **changed**

---

## D5 — Scope Realism

**Decision**: **Commit only to PRs 1–6**, re-plan after PR 6 ships.

**PR Order (revised based on evidence)**:

1. **PR 1**: Custom Plane foundation & documentation (current)
2. **PR 2**: **Milestones & timeline** (moved up — most reuse, no blocker)
3. **PR 3**: Company organizational structure (depends on D2)
4. **PR 4**: Custom RBAC (policy layer)
5. **PR 5**: Approval workflow (needed for timesheets)
6. **PR 6**: Timesheet & timer (depends on approval engine)

**Deferred (re-plan after PR 6)**: Modules 7–15 (Reporting, Workload, Risks, Automation, Documents, Notifications, Audit, OKRs, AI)

**Rationale**:

- Modules 5, 6, 8, 9, 14, 15 are full builds from zero
- Milestones has substantial reuse (Cycles, dependency vocabulary, Gantt seams)
- Approval engine is prerequisite for timesheet submission flow

---

## D6 — AGPL-3.0 Network-Use Obligation

**Decision**: **Acknowledged as hard gate**. Custom modules in this repo are a derivative work of Plane (AGPL-3.0). Offering the result as a network service triggers the source-offer obligation (Section 13).

**Action Required**: Legal review **before PR 1 merges**. Options:

- Comply: Offer complete corresponding source to users (including custom modules)
- Dual-license: Negotiate commercial license with Plane (makeplane.io)
- Architectural separation: Ship custom modules as a separately licensed package (complex)

**Current Stance**: Proceed with implementation under AGPL-3.0 compliance assumption. Legal sign-off required before any production deployment.

---

## D7 — Production Kubernetes Strategy

**Decision**: **Author new Helm charts** (not fork `plane-ce`). The repo's `deployments/kubernetes/community/` is a README pointing to external chart `makeplane/plane-ce` on `helm.plane.so` — no manifests to extend.

**Rationale**:

- Forking `plane-ce` adds upstream sync burden for K8s configs
- Custom charts can reference upstream images, add custom modules as sidecars/init-containers
- Simpler to maintain: custom values file overlays upstream chart

**Implementation**:

```
deployments/kubernetes/custom/
├── Chart.yaml
├── values.yaml           # Custom overrides
├── templates/
│   ├── custom-api-deployment.yaml
│   ├── custom-worker-deployment.yaml
│   ├── custom-migrations-job.yaml
│   └── custom-ingress.yaml
└── charts/
    └── plane-ce-<version>.tgz  # Upstream chart as dependency
```

---

## Summary: Approved Decisions

| Decision | Choice                                              | PR Impact        |
| -------- | --------------------------------------------------- | ---------------- |
| D1       | `plane/custom/<module>/` apps                       | All PRs          |
| D2       | Company (reporting) + Department (workspace-scoped) | PR 3             |
| D3       | Restrict-only policy layer                          | PR 4             |
| D4       | Custom trunk + tag merges                           | Ongoing          |
| D5       | PRs 1–6 only, re-plan after                         | Roadmap          |
| D6       | AGPL-3.0 compliance (legal sign-off needed)         | Pre-PR1 merge    |
| D7       | Author new Helm charts                              | PR 1 scaffolding |

---

**Next**: PR 1 — Custom Plane foundation and documentation
