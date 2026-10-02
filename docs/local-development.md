# Local development

## Docker-only startup

```sh
cp .env.example .env
docker compose --profile core up --build -d --wait
# Full profile includes core services; no need to specify both profiles.
AEGIS_TEMPORAL_ENABLED=true AEGIS_OTEL_ENABLED=true docker compose --profile full up --build -d --wait
docker compose exec worker python scripts/temporal_smoke.py
docker compose --profile full logs --tail=50 api worker
```

Compose initializes the PostgreSQL schema with a one-shot `migrate` service and creates the S3 bucket with `minio-init`. API startup waits for both. Local dummy credentials are safe for this loopback-only setup, never production. The source-built MinIO stage builds third-party infrastructure, not application backend code; no host Go toolchain is required. Its upstream source archive is versioned and checksummed. Build inputs and registry access require network access on first startup.

Default ports: API 8000, web 3000, PostgreSQL 5432, Redis 6379, MinIO 9000/9001, Temporal 7233/8233, Prometheus 9090, Grafana 3001, Loki 3100, OTLP 4318. All host bindings use 127.0.0.1. Do not expose this stack to public networks. Adjust `AEGIS_API_PORT`, `AEGIS_WEB_PORT`, `AEGIS_POSTGRES_PORT`, `AEGIS_REDIS_PORT`, `AEGIS_MINIO_PORT`, `AEGIS_MINIO_CONSOLE_PORT`, `AEGIS_TEMPORAL_PORT`, `AEGIS_TEMPORAL_UI_PORT`, `AEGIS_PROMETHEUS_PORT`, `AEGIS_GRAFANA_PORT`, `AEGIS_LOKI_PORT`, `AEGIS_OTEL_PORT` in `.env` if another application occupies a port. Also update host connection URLs, `NEXT_PUBLIC_API_URL` and CORS origins for host development. Internal Compose addresses are independent of host port overrides.

The full Temporal development server has its own persisted SQLite workflow history and automatic `default` namespace; application records remain PostgreSQL. It is explicitly a development server, not a hardened self-hosted production Temporal installation. See [upstream reference](https://docs.temporal.io/cli/command-reference/server).

## Host development

```sh
uv sync --frozen
pnpm install --frozen-lockfile
docker compose --profile core up -d postgres redis minio minio-init
uv run alembic upgrade head
uv run uvicorn apps.api.main:app --reload --port 8000 --no-access-log
# Another terminal:
cp .env.example apps/web/.env.local
pnpm web:dev
# Optional full workflow dependencies:
docker compose --profile full up -d temporal
uv run python -m apps.worker.main
uv run python scripts/temporal_smoke.py
```

Copying the example for web supplies dummy values only; the frontend uses `AEGIS_API_INTERNAL_URL` server-side and `NEXT_PUBLIC_API_URL` in links. `.env.local` is ignored. Next.js does not load the root `.env` automatically during host development. Stop `api`, `web` and `worker` first if switching from the full Docker stack to host processes.

## Verification

`make check` runs all service-independent CI gates. `make check-integration` opts into real PostgreSQL/Redis/S3/Temporal tests and exercises migration upgrade → check → downgrade → upgrade → check in an owned scratch database, then drops only that database. It requires a local development DB user able to create a scratch database. Tests use synthetic content and roll back persistence fixtures; S3 fixture objects are removed in `finally`. `make check-e2e` checks the actual API and SSR status page. Override `AEGIS_TEST_API_URL` and `AEGIS_TEST_WEB_URL` for alternate host ports.

Normal CI does not require Docker/Temporal/cloud credentials. A separate PostgreSQL-only migration job uses a free service container. Dependency audits query public advisory services; they do not need paid services. `make audit` audits the locked runtime Python requirements and frontend production dependencies. Audit findings block CI; exceptions require rationale rather than blanket suppression.

## Observability and shutdown

Send `X-Request-ID: local-example` / `X-Correlation-ID: local-correlation` to `/health`; inspect the same values in API JSON logs. With OTel enabled, send a W3C `traceparent` to `/api/v1/system/info` (`/health` and `/metrics` are excluded from tracing); inspect trace IDs in the log and collector's debug export. Metrics: `/metrics`. Grafana provisions Prometheus and Loki; Loki log selector `{service="aegisnews-api"}`. Alloy reads only the application log volume. No Docker socket is mounted. File logging rotates at 10 MB with two backups; production retention/export is deferred. Restart processes after changing telemetry settings.

```sh
docker compose --profile full down
```

This retains local data. `down -v` deletes this Compose project's local volumes; use it only when deliberately discarding local synthetic development data. No Kubernetes or cloud configurations are supplied.
