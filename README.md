# AegisNews

A standalone Secure Multimodal News Intelligence Platform, beginning as an academic Information Security + Cryptography + AI project. Its contracts and boundaries support long-term development and independent consumers.

**This branch contains foundation work only.** No news ingestion, AI inference, trading signals, production authentication, or cryptographic features are implemented. AegisNews has no dependency on Stockwise, portfolios, backtesting engines, or ticker applications.

## Architecture

```text
Next.js status shell → FastAPI /api/v1 → canonical domain/contracts
                                      → PostgreSQL source of truth
                                      → S3-compatible object storage
Test trigger → Temporal workflow → Python worker activity
Domain write + outbox write → one DB transaction → future asynchronous publisher
```

A modular monolith plus background workers. Python modules retain explicit boundaries; the API and worker share the same application package and database. Redis is ephemeral. PostgreSQL FTS, pg_trgm and pgvector are the intended search foundation. Kafka is optional future transport, behind `EventPublisher` and an outbox.

Stack: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL/pgvector, Redis, S3/MinIO, Temporal; Next.js, React, TypeScript, Tailwind; OpenTelemetry, Prometheus, Grafana, Loki. Tooling: uv, Ruff, mypy, pytest, pnpm, ESLint.

## Local setup

Prerequisites: Git, Docker Compose v2+, Python 3.12, uv, Node 22+, pnpm 10.33.1. Docker-only startup does not require host language toolchains.

```sh
cp .env.example .env
docker compose --profile core up --build -d --wait
```

Open [web](http://localhost:3000), [API docs](http://localhost:8000/docs), [health](http://localhost:8000/health), [readiness](http://localhost:8000/ready), and [MinIO console](http://localhost:9001). Local dummy console credentials are documented in `.env.example`. Migrations and the object-storage bucket are initialized automatically before the API starts.

```sh
AEGIS_TEMPORAL_ENABLED=true AEGIS_OTEL_ENABLED=true docker compose --profile full up --build -d --wait
docker compose exec worker python scripts/temporal_smoke.py
```

Full profile also provides Temporal UI :8233, Prometheus :9090, Grafana :3001, Loki :3100 and an OTLP HTTP receiver :4318. The smoke workflow is a connectivity example, not a news workflow. MinIO is built from a checksummed official source release because its published images are unavailable; the first build is slower. See [local development](docs/local-development.md).

## Development and validation

```sh
uv sync --frozen
pnpm install --frozen-lockfile
uv run uvicorn apps.api.main:app --reload --port 8000 --no-access-log
pnpm web:dev
# In a separate terminal, when the full profile is running:
uv run python -m apps.worker.main
uv run python scripts/temporal_smoke.py
```

Avoid running two workers on the same task queue unless deliberately testing multi-worker behavior. For host development, stop Compose API/web/worker while retaining dependencies; see the development guide.

```sh
make check                 # format, lint, mypy, unit/contract/security, schema drift, web lint/types/build
make check-integration     # live dependency, persistence, storage, Temporal tests + scratch migration roundtrip
make check-e2e             # HTTP status-page smoke against running API and web
make audit                 # Python and JavaScript dependency audits
uv run python scripts/export_schemas.py
uv run alembic upgrade head
```

Default pytest does not need Docker, Temporal, or credentials. Live checks are opt-in and use synthetic fixtures. The HTTP E2E smoke checks SSR output; browser interaction tests with Playwright are deferred.

## Repository structure

```text
apps/                 api/, web/, worker/ process entrypoints
aegis/                domain/, contracts/ architectural core
                      ingestion/, media/, normalization/, intelligence/
                      entities/, events/, provenance/, security/, observability/
                      persistence/ SQLAlchemy adapter
ml/                   models/, training/, evaluation/, datasets/ reserved
schemas/              openapi/, events/, domain/ exported v1 contracts
infrastructure/       docker/, temporal/, monitoring/
migrations/           Alembic migration history
tests/                unit/, contract/, integration/, security/, e2e/
docs/                 architecture, contracts, security, development, ADRs
data/samples/         synthetic samples only
scripts/              schema export and validation triggers
```

## Engineering principles

- Keep publication, observation, persistence and downstream availability times distinct.
- Freeze/version analysis outputs; never replace historical inference silently.
- Separate canonical entities from asset identifiers and facts from model outputs.
- Use cursor pagination and stable API errors; version asynchronous envelopes.
- Commit domain data and outbox envelopes together; publishing is at least once in the future.
- Keep business logic independent of infrastructure adapters and downstream financial consumers.
- Store secrets outside Git; local-only ports and dummy credentials are not a production security configuration.

Read [architecture](docs/architecture.md), [domain model](docs/domain-model.md), [API contracts](docs/api-contracts.md), [events](docs/events.md), [security boundaries](docs/security-boundaries.md) and [ADRs](docs/adr/README.md).

## Current status and next phase

Implemented: versioned contracts and exported schemas; minimal API/status shell; foundational schema/outbox; typed extension ports; local infrastructure and Temporal smoke workflow; observability and CI. Product route modules are empty and return the standard 404 envelope. Models and datasets are not installed.

Next phase: **Ingestion + Normalization**. Preserve raw content and its timestamps; add a single synthetic/feed ingestion path before adding AI. Read [foundation handoff](docs/foundation-handoff.md) for validation evidence and limitations.
