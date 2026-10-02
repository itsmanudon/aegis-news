# Foundation handoff

Foundation branch: `chore/aegisnews-foundation`, pushed at `3799486a59cf495a57597db64af5229e272ac627`. Its original base is initial commit `0935946`; original local validation used `/private/tmp/aegisnews-foundation`. Contract hardening is on `chore/aegisnews-contract-hardening`, branched from that exact foundation SHA. The hardening branch is committed locally without merge or push. Resolve its final identifier with `git rev-parse HEAD`. No product implementation or cloud deployment is included.

## Delivered scope

The modular monolith contains versioned, frozen canonical records and transport envelopes; the minimal FastAPI application and Next.js status shell; SQLAlchemy persistence, an initial Alembic migration and atomic outbox staging; S3 adapter, crypto/model ports and a no-op publisher; and a Temporal demonstration workflow with worker activity. Eight ADRs cover the architecture, persistence, orchestration, outbox, search, storage, entity/asset separation and immutable analysis decisions.

`0001_foundation` creates 14 tables: sources, raw_objects, ingestions, documents, media_assets, entities, entity_mentions, asset_mappings, analyses, events, event_documents, event_entities, provenance_records and outbox_events. It enables vector/pg_trgm and rejects analysis UPDATE/DELETE/TRUNCATE. Source `published_at` is distinct from transport `dispatched_at`. Downgrade drops application tables and the trigger function but retains potentially shared extensions; use destructive reversal only on owned local scratch data.

Compose core: PostgreSQL, Redis, source-built MinIO, bucket initialization, migrations, API and web. Full adds Temporal, worker, Prometheus, Grafana, Loki, Alloy and an OTel collector. Application containers run as non-root users; all host ports bind to loopback. The initial MinIO build uses its upstream Go toolchain only inside a build stage because official container registries failed to provide the approved service.

## Validation evidence

The following checks were executed locally on 2026-10-02:

- `make check`: Ruff format/lint, strict mypy, default pytest, schema drift check, frontend ESLint, TypeScript with generated route types, and Next.js production build.
- Full pytest with `AEGIS_RUN_INTEGRATION=1 AEGIS_RUN_E2E=1`: **49 passed**, covering unit, contract, security, live integration and HTTP E2E scopes. The default suite has **43 passed, 6 intentionally skipped** until services are enabled.
- PostgreSQL-only CI selection: all three database tests passed.
- `scripts/verify_migrations.py`: fresh upgrade, Alembic metadata check, downgrade, upgrade, metadata check; owned scratch DB removed afterward.
- Full Compose `up --build -d --wait`: successful; PostgreSQL, Redis, MinIO, Temporal, API and web health checks passed. One-shot initialization/migration containers exited successfully.
- Temporal smoke script inside the worker container: completed with `AegisNews foundation: smoke`.
- Real S3 put/get/delete/exists/metadata roundtrip, outbox commit/rollback/deduplication and immutable-analysis SQL checks passed.
- Request/correlation headers and W3C trace ID verified in structured request logs; URL/query redaction verified. Prometheus target up, Grafana Prometheus/Loki provisioning and Loki application log ingestion passed. Collector received traces.
- Runtime Python/frontend dependency audits: no known vulnerabilities. Gitleaks checked the complete staged change with redacted output; no secrets found.

Alternate host ports were used to avoid existing applications: API 18080, web 13000, PostgreSQL 15432, Redis 16379, MinIO 19000/19001, Temporal 17233/18233, Prometheus 19090, Grafana 13001, Loki 13100, OTLP 14318. These overrides are in an ignored local `.env`; the committed example uses conventional ports.

GitHub Actions defines backend, frontend, PostgreSQL migration/transaction tests and security jobs with read-only repository permissions, bounded timeouts and cancellation of stale runs. No normal PR job needs Temporal, Kafka, cloud credentials or paid infrastructure. Hosted GitHub Actions ran successfully on foundation commit `3799486a59cf495a57597db64af5229e272ac627`: backend, frontend, migrations and security all succeeded. This hosted evidence applies to the foundation commit; the unpushed hardening commit has local validation evidence only.

## Contract hardening

All six model protocols now return `AnalysisResult`. New domain outputs are `EntityExtractionResult`, `EmbeddingResult` and `EventExtractionResult`; they share the existing immutable metadata/time lineage. Canonical mentions/events can later be derived with `evidence_kind="model_output"` and `analysis_id`, while facts must have no analysis reference. No derivation service or inference is implemented. Event classification requires `event_id` plus explicit `event_revision >= 1`; pre-hardening classification payloads lacking revision are intentionally rejected, without modifying old database analyses.

`DocumentMediaLink` and its composite-key `document_media` table provide explicit many-to-many membership, independent of ingestion identity. Forward migration `0002_contract_hardening` adds the table and reverse index; migration `0001_foundation` and analysis append-only triggers are preserved. No implicit backfill, role/order metadata, or cascading deletion is introduced. All new outputs, existing entity resolution/classification outputs and the link are exported as public JSON schemas. Async envelopes retain v1 unchanged.

### Hardening validation on Windows, 2026-10-02

Locked dependencies were installed with `uv sync --frozen --python 3.12` and `pnpm.cmd install --frozen-lockfile`. GNU Make from MSYS was added to PATH. Final checks:

```powershell
$env:PATH = 'C:/msys64/usr/bin;' + $env:PATH
make check
uv run python scripts/verify_migrations.py
$env:AEGIS_RUN_INTEGRATION = '1'
uv run pytest -q -m database --tb=short
docker compose --profile core up --build -d --wait
docker compose --profile core up -d --wait
$env:AEGIS_TEMPORAL_ENABLED = 'true'
$env:AEGIS_OTEL_ENABLED = 'true'
docker compose --profile full up --build -d --wait
docker compose exec -T worker python scripts/temporal_smoke.py
$env:AEGIS_REDIS_URL = 'redis://127.0.0.1:6379/0'
$env:AEGIS_RUN_E2E = '1'
$env:AEGIS_TEST_API_URL = 'http://127.0.0.1:28080'
$env:AEGIS_TEST_WEB_URL = 'http://127.0.0.1:23000'
uv run pytest -q --tb=short
```

- `make check` passed: format/lint, strict mypy, **114 passed, 11 opt-in skips**, schema drift, frontend lint/types/build.
- Scratch migration verification passed: upgrade/check, downgrade to `0001_foundation`, upgrade/check, downgrade to base, upgrade/check. Owned scratch databases were removed. Verification also passed inside the API container (`docker compose exec -T api python scripts/verify_migrations.py`).
- PostgreSQL-only tests: **8 passed**, including five analysis output variants with UPDATE/DELETE/TRUNCATE rejection, independent model upgrades, timestamp checks, explicit shared media, duplicate rejection and both endpoint foreign keys.
- Core images built successfully. Initial startup attempts hit occupied ports; rerunning core with the ignored local port overrides passed. Full Compose build/start/wait passed with all services running and initialization/migration jobs completed.
- Temporal smoke completed with `AegisNews foundation: smoke`. The full live unit/contract/security/integration/HTTP E2E suite passed: **125 passed, no skips**.
- Initial host database attempts timed out during port reconfiguration. PostgreSQL and Redis host validation used explicit IPv4; an initial full-suite Redis localhost readiness failure was resolved by that configuration. No application behavior was changed to work around the host.
- Two non-failing warnings remain: the existing Starlette TestClient deprecation and a Windows pytest cache permission warning.

Hardening validation used API 28080, web 23000, PostgreSQL 25432, Redis 6379, MinIO 29000/29001, Temporal 27233/28233, Prometheus 29090, Grafana 23001, Loki 23100 and OTLP 24318. These are local `.env` overrides; no Compose defaults changed. The hardening commit has not been pushed or run in hosted CI.

## Limitations and intentional deferrals

Foundation validation establishes local behavior, not production readiness. Temporal is a development server with persisted internal SQLite history; production Temporal deployment, authentication, RBAC, TLS, restricted DB roles, key management and all actual crypto/provenance features are deferred. The OpenTelemetry collector is a debug sink; there is no trace database or custom dashboard. Worker log/trace propagation is not implemented. There is one non-failing upstream Starlette warning about the httpx-based TestClient.

IDs use centralized prefixed UUID4; UUIDv7 can replace generation without changing wire shape. Domain validation is required before direct ORM/SQL writes; not every canonical enum/cross-record lineage rule is enforced in SQL. Analysis metadata does not itself preserve model binaries/configuration artifacts. Schema owners can bypass triggers; controlled deletion/retention requires a future policy.

The local publisher intentionally discards events. No outbox dispatcher, delivery retry/dead-letter loop or Kafka adapter exists. Object storage and PostgreSQL are separate transaction domains; orphan cleanup/object immutability awaits ingestion design. Browser interactions/Playwright, live providers, scraping, normalization, AI inference/training, multimodal processing, signatures, search behavior, financial consumers, OpenSearch, Kafka, Kubernetes and cloud deployment are intentionally absent.

## Recommended next task

**Agent 1: Ingestion + Normalization.** Branch from the validated contract-hardening commit when it is adopted as the shared base. Start with one synthetic or explicitly licensed feed path. Preserve raw bytes and source claims; establish idempotent observation, exact first-seen/ingestion times, object naming/recovery, canonical document creation, and transactional domain/outbox writes. Add a genuine NewsIngestionWorkflow incrementally with failure/retry tests. Keep model inference, trading logic and consumer-specific integrations outside that phase unless separately authorized. Agent 0.1 stops after contract hardening.
