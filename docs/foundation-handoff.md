# Foundation handoff

Branch: `chore/aegisnews-foundation`. Isolated worktree used for validation: `/private/tmp/aegisnews-foundation`. Base: initial commit `0935946`. Foundation changes are committed locally; no merge, push, cloud deployment or ingestion phase is performed. Resolve the final identifier with `git rev-parse HEAD` on this branch.

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

GitHub Actions defines backend, frontend, PostgreSQL migration/transaction tests and security jobs with read-only repository permissions, bounded timeouts and cancellation of stale runs. No normal PR job needs Temporal, Kafka, cloud credentials or paid infrastructure. Hosted Actions have not been run because the branch was not pushed.

## Limitations and intentional deferrals

Foundation validation establishes local behavior, not production readiness. Temporal is a development server with persisted internal SQLite history; production Temporal deployment, authentication, RBAC, TLS, restricted DB roles, key management and all actual crypto/provenance features are deferred. The OpenTelemetry collector is a debug sink; there is no trace database or custom dashboard. Worker log/trace propagation is not implemented. There is one non-failing upstream Starlette warning about the httpx-based TestClient.

IDs use centralized prefixed UUID4; UUIDv7 can replace generation without changing wire shape. Domain validation is required before direct ORM/SQL writes; not every canonical enum/cross-record lineage rule is enforced in SQL. Analysis metadata does not itself preserve model binaries/configuration artifacts. Schema owners can bypass triggers; controlled deletion/retention requires a future policy.

The local publisher intentionally discards events. No outbox dispatcher, delivery retry/dead-letter loop or Kafka adapter exists. Object storage and PostgreSQL are separate transaction domains; orphan cleanup/object immutability awaits ingestion design. Browser interactions/Playwright, live providers, scraping, normalization, AI inference/training, multimodal processing, signatures, search behavior, financial consumers, OpenSearch, Kafka, Kubernetes and cloud deployment are intentionally absent.

## Recommended next task

**Agent 1: Ingestion + Normalization.** Branch from this foundation commit. Start with one synthetic or explicitly licensed feed path. Preserve raw bytes and source claims; establish idempotent observation, exact first-seen/ingestion times, object naming/recovery, canonical document creation, and transactional domain/outbox writes. Add a genuine NewsIngestionWorkflow incrementally with failure/retry tests. Keep model inference, trading logic and consumer-specific integrations outside that phase unless separately authorized.
