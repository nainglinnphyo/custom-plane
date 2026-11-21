# 15 — Upstream Maintenance

## 1. Model (from D4)

Long-lived `custom/main` that **merges release tags** from `upstream` (never `preview`). Current base: `v1.5.0` (`18caf808a3`). Remotes verified: `origin` = fork, `upstream` = `makeplane/plane`.

```bash
git fetch upstream --tags
git checkout -b sync/v1.6.0 custom/main
git merge v1.6.0          # tag, not a branch
# resolve conflicts → run full backend suite, pnpm check, UAT compose smoke → PR into custom/main
```

Rehearse on `-rcN` tags first (upstream publishes 1–3 per release: `v1.5.0-rc1/rc2` exist). No force-push, no rebasing of shared history.

## 2. Conflict surface (what we own that upstream also touches)

| File                                        | Edit                                                                                           | Risk                                                                                              |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `apps/api/plane/settings/common.py`         | +2 lines in `INSTALLED_APPS` (proposed: replace with one `CUSTOM_INSTALLED_APPS` splat)        | Low; `INSTALLED_APPS` changes occasionally                                                        |
| `apps/api/plane/urls.py`                    | +2 lines (`api/custom/`)                                                                       | Low                                                                                               |
| `docker-compose-local.yml`                  | Postgres host port 5435                                                                        | Low–Med (compose file changes upstream; local only)                                               |
| `apps/api/migrations_lockfile.txt`          | gains `custom_*` lines                                                                         | Low — blank-line-separated per app to avoid conflicts                                             |
| Frontend `*extended*` seams                 | custom content                                                                                 | Medium — upstream may start filling them; keep custom code in separate files imported by the seam |
| `packages/i18n/src/constants/namespaces.ts` | +1 entry (`milestone`)                                                                         | Low — alphabetical list; every new custom namespace adds a line                                   |
| `apps/web/app/routes/extended.ts`           | custom routes (seam)                                                                           | Low–Med — upstream may fill the seam                                                              |
| `apps/web/package.json`, `pnpm-lock.yaml`   | `vitest` devDependency + `test` script                                                         | Low — re-run `pnpm install` on conflict                                                           |
| Everything else                             | none (all under `plane/custom/`, `docs/`, `apps/web/components/milestones/`, new locale files) | none                                                                                              |

## 3. Per-sync checklist

1. `git diff <old-tag>..<new-tag> -- <list of files above>` and the permission modules (`plane/app/permissions`, `plane/utils/permissions`), `db/models/base.py`, `workspace.py`, `issue.py`, `project.py`, `celery.py`.
2. Check whether any seam file changed from its no-op state.
3. Run `makemigrations --check` — core model changes that affect our FKs surface here.
4. Check upstream changes to `uv.lock`/Python/Node/pnpm versions and the compose images.
5. Run the full suite + custom suite + UAT smoke.
6. Update `docs/02-REPOSITORY-ANALYSIS.md` facts (versions, counts).

## 4. Cadence

Upstream releases roughly every 4–8 weeks (D4 claim, based on the 68 tags present; not re-derived). Sync on every minor release; security patches ASAP. Skip RCs in production.

## 5. Risks

- Upstream renames/refactors a model we FK to → custom migration breakage.
- Upstream consolidates the two permission modules → our policy decorator must be re-validated (contract test, 06 §6).
- Upstream fills `extended` seams (they are placeholders upstream) → conflict in UI hook files.
- AGPL: obligations continue for every release we deploy (D6).
- Single maintainer knowledge risk — keep this doc and `DECISIONS.md` current.

## 6. Extra per-sync check (added in PR 2)

Re-grep for upstream Milestones code arriving in CE: `git grep -il milestone -- apps packages ':!apps/api/plane/custom'` and compare against the placeholders listed in `02-REPOSITORY-ANALYSIS.md` §7a.
