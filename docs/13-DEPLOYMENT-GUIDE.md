# 13 — Deployment Guide

Strategy (from `prompt.md`): Docker Compose for local, UAT and production. **Production configs are not modified in this phase.** Secrets are never recorded here.

## 1. Environments

| Env           | Compose file                                                                                                | What runs in containers                                                                                                            |
| ------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Local dev     | `docker-compose-local.yml`                                                                                  | redis(valkey 7.2), rabbitmq 3.13, minio(silo), postgres 15.7, api, worker, beat-worker, migrator. Frontends on host via `pnpm dev` |
| UAT / Prod    | `docker-compose.yml` (builds from repo) or `deployments/cli/community/docker-compose.yml` (registry images) | web, admin, space, api, worker, beat-worker, migrator, live, db, redis, mq, minio, proxy                                           |
| Backend tests | `docker-compose-test.yml`                                                                                   | isolated api-tests stack                                                                                                           |

Custom code is part of `apps/api` (`COPY plane plane/` in `Dockerfile.api`), so **the same api/worker/beat/migrator images carry it**; no new service. The migrator runs custom migrations automatically on deploy.

Kubernetes: the repo holds only a README pointing at the external Helm chart `makeplane/plane-ce`. D7 proposes authoring a separate overlay chart; since upstream's chart pulls upstream images, a custom-image chart/values override is required for custom code. Not needed for Compose.

## 2. Local environment status (verified 2026-11-21, this machine)

| Check                                                   | Result                                                                                                                                                                                                                                    |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Docker 27.4.0 / Compose v2.31.0                         | OK; Docker VM: 8 CPUs, ~5.8 GiB RAM (tight for the full stack + other containers)                                                                                                                                                         |
| Host                                                    | 10 cores, 32 GiB, 5.7 TiB free disk                                                                                                                                                                                                       |
| Env files                                               | `.env`, `apps/api/.env`, `apps/web/.env` already exist (git-ignored). Not overwritten; values not printed. `setup.sh` **not re-run** (it overwrites env files with `cp`)                                                                  |
| Tool versions                                           | `uv 0.12.21` ✓ (matches required); `Python 3.15` on host (backend runs in Docker with 3.12 — OK); `pnpm` via corepack **fails** under nvm Node 22.12 (signature/keyid error); Node 22.22.0 is installed in nvm, repo requires `>=22.22.0` |
| `plane-db` (Postgres)                                   | Up; `pg_isready` accepting connections; host port **5435**                                                                                                                                                                                |
| `plane-redis`                                           | Up; `PONG`; host port 6379                                                                                                                                                                                                                |
| `plane-mq` (RabbitMQ)                                   | Up; ping OK                                                                                                                                                                                                                               |
| `plane-minio`                                           | Up; ports 9000/9090                                                                                                                                                                                                                       |
| `api`                                                   | Up; `GET /` 200, `GET /api/instances/` 200, `GET /api/custom/health/` 200                                                                                                                                                                 |
| `worker`, `beat-worker`                                 | Up                                                                                                                                                                                                                                        |
| `migrator`                                              | Exited 0 (expected, one-shot)                                                                                                                                                                                                             |
| Web `:3000`, admin `:3001`, space `:3002`, live `:3100` | **Not Plane.** Those ports are occupied by other projects' dev servers (`Mee Timeline`, `fary-v3`). Plane frontends were **not started** and those processes were not touched                                                             |

### Findings

1. **Port collision for frontends** — free the ports or run Plane's apps on alternates; requires a decision (changing ports touches `.env`/vite config).
2. **Services bind to all interfaces.** `docker-compose-local.yml` publishes `6379`, `9000`, `9090`, `5435`, `8000` as `"port:port"` (0.0.0.0). That exposes Redis (no auth configured in compose), MinIO and Postgres to the local network. Recommended: bind to `127.0.0.1:` (change not made — needs approval).
3. Valkey/Redis port 6379 collides with other local projects' containers (one exited container also maps 6379).
4. Docker VM memory (~5.8 GiB) is shared with ~19 containers from other projects.
5. `pnpm` corepack breakage under Node 22.12; use the 22.22.0 nvm install (`nvm use 22.22.0`) before `corepack enable pnpm`.

### Commands (documented upstream flow)

```bash
./setup.sh                                   # first time only; overwrites env files — do not re-run on a configured checkout
docker compose -f docker-compose-local.yml up -d
pnpm install && pnpm dev                     # web 3000, admin 3001, space 3002, live 3100
docker compose -f docker-compose-local.yml logs -f api
curl -s localhost:8000/api/custom/health/
```

## 3. UAT / Production notes (design only)

- Build images from `custom/main` tags (`custom-vX.Y.Z+plane-A.B.C`) — scheme to be approved.
- Pin all upstream image tags (already pinned in compose); secrets from env/secret store, not the repo.
- Terminate TLS at the Caddy proxy (`apps/proxy`); do not expose Postgres/Redis/RabbitMQ/MinIO ports on the public interface.
- Backups: reuse `deployments/cli/community` backup/restore scripts (not evaluated).
- AGPL-3.0: offering a hosted instance requires making the corresponding source (incl. custom modules) available to users — legal sign-off first (D6).
- UAT = prod topology with separate env, separate DB and bucket.
