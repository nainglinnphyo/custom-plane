# 07 — Approval Workflow (PROPOSED)

## 1. Existing capability

None. A repo-wide search finds no approval/approver concept in `apps/api/plane` (only unrelated mentions in `settings/openapi.py`). `apps/web/components/workflow` is a small stub (`index.ts`, a drag-and-drop hook) and is not an approval engine. Intake (triage) is the closest existing review concept but is specific to inbound work items.

## 2. Design

A generic engine so timesheets (first subject) and later modules (risks, documents, OKR changes) reuse it.

```
Subject (Timesheet) ──submit──► ApprovalRequest(pending, step 1)
   step approver approve ──► next step … ──► last step approve ──► Request approved ──► subject adapter.on_approved()
   any approver reject  ──► Request rejected ──► adapter.on_rejected()  (subject returns to draft)
   requester cancel     ──► cancelled
```

### State machine

`ApprovalRequest.status`: `pending → approved | rejected | cancelled | expired`. `ApprovalStep.status`: `pending → approved | rejected | skipped`.
Only the active step's approver (or workspace Admin override, logged) may act; each action is written to the append-only `ApprovalAction` table inside the same DB transaction as the state change (`select_for_update` on the request row to prevent double-approval races).

### Approver resolution (configurable per `ApprovalFlow.steps_definition`)

Supported rule types (to confirm with product owner): specific user; project lead (`Project.project_lead`); department head (module 1); role-based. Self-approval blocked by default.

### Subject adapters

Each subject registers `on_submit / on_approved / on_rejected / lock_subject` in `plane/custom/approvals/registry.py`. Timesheet adapter: locks its `TimeEntry` rows on submit, unlocks on reject.

### Notifications

On step activation and completion: create core `Notification` rows (existing model) or custom channel once module 12 exists; email via the existing stacked email task is **not** reused until verified.

### Background tasks

Beat task `expire_stale_requests` and optional reminder/escalation task. Runs via the existing Celery infra.

## 3. API

See 05 §3 (Approvals).

## 4. Authorization

Step approver or workspace Admin; policy layer may deny. Request visibility: requester, approvers, Admins.

## 5. Testing

State-machine table tests (every transition, illegal transitions rejected), concurrency test for double-approve, permission matrix, subject-adapter contract test.

## 6. Open questions

Delegation, escalation timeout, parallel approvals, re-submission after rejection (new request vs reopen), audit retention.
