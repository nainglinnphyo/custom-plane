# 01 — Product Requirements

> **Status: skeleton, not a signed-off PRD.** No requirements document was supplied. The only product inputs are the module list and PR sequence in `prompt.md`. Anything beyond that is marked **PROPOSED** and needs the product owner's confirmation. Nothing here is invented as fact about the business.

## 1. Goal

Extend Plane (AGPL-3.0, pinned at `v1.5.0`) into "Custom Plane" for company-level project delivery: organizational structure, tighter access control, milestones, time tracking with approval, reporting, and later planning/AI features — as a **modular monolith** (same Django project, same containers).

## 2. Scope by module (from `prompt.md`)

| #    | Module                                                                            | Committed phase                           | Plane already provides                         | Gap to build                                |
| ---- | --------------------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------------- | ------------------------------------------- |
| 1    | Company & departments                                                             | PR 2/3                                    | Workspace, `WorkspaceMember.company_role` text | Hierarchy of departments, company grouping  |
| 2    | Teams & memberships                                                               | with 1                                    | dormant `Team` model, no members               | Membership, API, UI                         |
| 3    | Custom RBAC                                                                       | next                                      | 3 fixed roles                                  | Fine-grained policy (restrict-only per D3)  |
| 4    | Milestones & timeline                                                             | next                                      | Modules, Cycles, relations, Gantt UI           | Milestone entity + dependencies on timeline |
| 5    | Timesheets & timer                                                                | next                                      | Project flag only                              | Everything                                  |
| 6    | Approval workflow                                                                 | next                                      | none                                           | Everything                                  |
| 7–15 | Reporting, workload, risks, automation, documents, notifications, audit, OKRs, AI | **Deferred** (re-plan after PR 6, per D5) | see 02 §7                                      | see 03 §4                                   |

## 3. Requirements to confirm (PROPOSED)

Each module needs acceptance criteria from the product owner. The questions below block detailed design:

**Company/Teams** — One workspace or many under one company? Are departments hierarchical? Can a person be in several departments/teams? Do teams own projects?
**RBAC** — Which concrete roles/permissions beyond Admin/Member/Guest? Are _grants_ needed (current design only restricts)?
**Milestones** — Per project or cross-project? Date source (manual vs derived from work items)? Dependencies between milestones?
**Timesheets** — Granularity (per work item? per project?), weekly submission period, billable flag, edit window after approval, timer rules (one active timer per user?).
**Approvals** — Who approves (manager, department head, project lead)? Single vs multi-step? Delegation/escalation? What happens on rejection?
**Reporting / AI / OKRs** — deferred; not specified.

## 4. Non-functional requirements (derived from the repo, not invented)

- Self-hosted via Docker Compose in dev/UAT/prod (per `prompt.md`).
- Must not regress upstream behavior; custom code isolated under `plane/custom/`.
- Respect AGPL-3.0 obligations (D6); legal sign-off precedes any production deployment.
- Must follow upstream conventions: soft delete, UUID PKs, audit fields, copyright headers, i18n keys, migration lockfile.
- Security: no secrets in docs/logs; custom endpoints require authentication and workspace/project membership checks.

## 5. Out of scope (until approved)

Any feature implementation beyond the PR 1 scaffold; production deployment changes; changes to core models.
