# 09 — Timesheet & Timer Design (PROPOSED)

## 1. What Plane already has

Only `Project.is_time_tracking_enabled` (boolean; also in `plane/api/serializers/project.py`) and the `Issue.estimate_point`/`point` estimation fields. **No time entries, timers, or timesheets exist.** Full build.

## 2. Design

- `TimeEntry` (manual or timer-generated), `ActiveTimer` (at most one per user — to confirm), `Timesheet` (user + period) — see 04 §5.
- **Timer**: `start` creates `ActiveTimer` and fails if one exists (or auto-stops the previous, configurable); `stop` creates a `TimeEntry` from `started_at → now` inside one transaction. Server time is authoritative (never trust client clocks). Use `Project.timezone` / user timezone only for display and period boundaries.
- **Sweeper**: beat task stops/flags timers running longer than N hours (value to be set by product owner).
- **Periods**: weekly by default (configurable later); a `Timesheet` is created lazily on first entry in a period.
- **Submission**: `submit` validates entries (no overlap if required, within enabled projects), recomputes `total_seconds`, locks entries, and creates an `ApprovalRequest` (module 6). Approved → status `approved`, entries immutable; rejected → back to `draft`, entries unlocked.
- **Gate**: entries allowed only on projects with `is_time_tracking_enabled`; user must be an active `ProjectMember` (not Guest — to confirm).
- Reporting feed for module 7 uses `TimeEntry` aggregates (indexed by `(user, started_at)`).

## 3. API / Frontend

API in 05 §3. UI: timer widget on work-item detail via an existing `extended` seam (candidate: `use-workspace-issue-properties-extended` / issue-detail extension — spike needed, unverified) and a "My timesheet" page via `routes/extended.ts`.

## 4. Authorization

Owner edits own entries while the timesheet is draft; Admin read; approvers act through the approval engine; policy layer may deny.

## 5. Background

Stale-timer sweeper; approval reminders.

## 6. Testing

Timer start/stop concurrency (double start), overlap rules, period boundary & DST/timezone cases, lock-after-submit, approval integration, rounding rules.

## 7. Upstream conflict risk

Low: new tables/app. UI hook on the work-item page is the only coupling.

## 8. Open questions

Billable/rate data? Minimum/maximum entry length? Retroactive edit window? Per-project vs global approval? Export format for payroll?
