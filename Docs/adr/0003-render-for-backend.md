# ADR 0003: Deploy the backend to Render

- **Status:** Proposed (becomes Accepted when Christopher has run it once on Render)
- **Date:** 2026-10-22
- **Owner:** Christopher
- **Supersedes:** the "one VPS + Docker Compose + Caddy" staging decision of 2026-10-16, once Render is verified. `deploy/staging/` stays until then.

## Scope

**Backend only.** Web and Flutter are not deployed; they start after the backend gate. Nothing in this ADR touches `web/` or `mobile/`.

## Context

The backend is stateless (API, Celery worker, Celery beat) with state in PostgreSQL/PostGIS, Redis and S3-compatible storage. It holds a money ledger and tamper-proof evidence. A single VPS means we patch, back up and restore it ourselves and it is a single point of failure.

## Decision

- Run the backend on Render from `render.yaml` at the repo root: `ibackhome-api` (web), `ibackhome-worker`, `ibackhome-beat` (background workers), Render Postgres 16 with PostGIS, Render Key Value (Redis). Region Frankfurt (nearest to Nigeria and to UK/EU users).
- Paid plans only. The API, worker and beat run all the time, and free web services sleep, free Postgres expires after 30 days.
- Photos stay in Cloudflare R2, outside Render, so storage does not depend on the compute host.
- Migrations run in `preDeployCommand` (`alembic upgrade head`), once per deploy.
- Deploys happen automatically after `backend-ci` passes on `main` (`autoDeployTrigger: checksPass`).
- Secrets live in the Render environment group `ibackhome-app`, never in the repo.
- `Settings.database_url` accepts `postgresql://` and rewrites it to `postgresql+psycopg://`, because Render's connection string has no driver name.
- Beat runs as exactly one instance. API and worker may scale out.

## Consequences

- Managed backups and point-in-time recovery for the ledger. We still need a nightly `pg_dump` to R2 and a tested restore before real money.
- Roughly $35–45/month for staging on these plans.
- `FORWARDED_ALLOW_IPS=*` because Render's proxy addresses are not fixed; it is safe only while the services are reachable solely through Render's proxy.
- Before more than a few API instances: add connection pooling (PgBouncer).
- The Dockerfile is unchanged, so moving to another host later is a configuration change.
- `render.yaml` has not been validated by Render yet; the first Blueprint sync will report any schema errors.
- CLAUDE.md "Staging" must be updated when this is Accepted.
