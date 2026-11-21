# 10 — Reporting Design (PROPOSED, deferred module 7)

## 1. Existing

`plane.analytics` app, `AnalyticView` model, analytics UI (`apps/web/components/analytics`, `store/analytics.store.ts`), export machinery (`bgtasks/export_task.py`, `analytic_plot_export.py`, `ExporterHistory`, S3 expiry cleanup), saved `IssueView`s, Cycle `progress_snapshot`.

## 2. Design direction

- Read-only query layer in `plane/custom/reporting/` over core + custom tables (time entries, milestones, departments); executed on the **read replica** switch (`ReadReplicaControlMixin`) when configured.
- Every query goes through the caller's RBAC (workspace/project membership + policy layer) — a report must never reveal data the user cannot open directly.
- Heavy reports run as Celery tasks and write files through the existing exporter/`FileAsset` path; results cached as `ReportSnapshot`.
- Initial report candidates (to be confirmed): time by project/user/department, milestone health, workload vs capacity, approval turnaround.

## 3. Risks

Query cost on large workspaces (needs indexes from 04 §8 and pagination), accidental cross-workspace aggregation, reuse of core analytics code that may change upstream.

## 4. Testing

Golden-data fixtures, query-count/perf budget tests, permission-filtering tests.

Detailed design is postponed until after PR 6 (D5).
