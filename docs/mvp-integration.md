# Integrated local MVP

The integration branch is `integration/mvp`, in `.worktrees/integration-mvp`, based exactly on `0203ae95aa1fdf75dd05862c404b5cc743a01f55`. Main and all feature worktrees remain untouched. Nothing was pushed.

## Integrated commits and conflict decisions

| Feature | Requested tip | Integration commits |
|---|---|---|
| Ingestion | `2043261183984efabeb824a085f3d46c138874d7` | `e1ce98b` |
| AI | `dc752ca6ed5df5b3a766f5a76e14145c5347cb38` | `2b8ded4`, `299e367` |
| Security | `c9837702cc0df96e4f0b6e3bd9269c4450a182be` | `b3c72da` |
| Frontend | `f5aec597f1d85c68ae0cdc4954a00fcf6a1246e5` | `70b45d6` |

AI's tip is a fix atop `c7f0af6`; both commits were required. A tip-only attempt was aborted, then the complete feature range applied cleanly. The only actual content conflict was `apps/api/main.py`: ingestion owns service lifecycle/body validation and security owns identity, scope checks, security middleware and CORS authorization headers. Both were retained. Product endpoints were then added with scope dependencies, including the document route originally owned by ingestion.

## Migration graph

```text
0001_foundation
    └── 0002_contract_hardening
            ├── ingestion_0001 ──┐
            └── security_0001 ───┴── mvp_merge_0001
```

Neither feature migration was rebased. `mvp_merge_0001` is a no-op merge revision with both heads as parents. A fresh, owned scratch database passed upgrade → metadata check → downgrade to foundation → upgrade → check → downgrade to base → upgrade → check. No populated production database was downgraded.

## Processing and evidence

`NewsIngestionWorkflow` executes `prepare_ingestion` (acquire/validate/hash/store raw and media/persist ingestion), `normalize_ingestion`, `commit_ingestion` (document, explicit media links and ingestion outbox), then independently retryable `analyze_entities`, `analyze_topics`, `analyze_sentiment`, `generate_embedding`, `resolve_entities`, `extract_events`, and `record_provenance`.

All storage, SQL, inference, wall-clock use, random IDs and cryptography stay in activities. Stable workflow/task IDs and transaction locks make repeated activities idempotent. A distinct analysis run key creates new immutable analyses. Each analysis, its permitted materializations and its outbox messages commit together. Provider/model/version/configuration hash/creation and availability times are preserved. Resolver output retains separate analysis lineage; extraction mentions remain model output and are not promoted into canonical entities. Curated demo entities are seeded independently. Events carry producing analysis IDs and revision-safe links. Existing classification contracts continue to require event ID and revision.

`AEGIS_AI_PROFILE=offline` is the default. It uses transparent keyword/lexicon/capitalized-span/hash-vector baselines, with no downloads. `light` and `full` use Agent 2's pinned local models and require separately installed optional dependencies and artifacts (`ml/models/requirements-local.txt`). Missing models, unsupported language and no predictions produce explicit unavailable stages while allowing normalized ingestion to complete. No empty or fabricated analysis is inserted. Full/light model quality and performance were not evaluated here.

Embeddings persist inside the immutable typed analysis outputs. `/documents/{id}/similar` casts compatible vectors to pgvector for cosine ranking; no additional vector database or heavyweight dependency is introduced. Offline vectors demonstrate lexical similarity, not learned semantic understanding. Light/full can use learned embeddings. This is an exact scan suitable for the small MVP; ANN indexing is deferred.

Provenance signs raw bytes, normalized document, analysis records, materialized mentions/events, explicit media links, media metadata and actual attachment hashes. Verification reads live SQL/object contents and checks all signed runs plus coverage of persisted analyses. SHA-256 detects content changes; Ed25519 authenticates the chain; AES-256-GCM encrypts a retrievable manifest archive bound to the document ID. Retry retrieval uses the exact run's provenance ID. Missing/changed content, changed provenance records and media/link tampering fail verification. TLS remains transport protection. Keys are generated into a private local volume and never committed.

## API and authorization

All product paths below have the `/api/v1` prefix. Collections use canonical envelopes and cursor pagination, except similarity, which is an explicit bounded top-k result.

| Method | Path | Scope in secured mode |
|---|---|---|
| POST | `/sources` | `sources:write` |
| GET | `/sources`, `/sources/{source_id}` | `sources:read` |
| POST | `/ingestions`, `/ingestions/batch` | `ingestions:write` |
| GET | `/ingestions/{ingestion_id}`, `/ingestion-runs/{workflow_id}` | `documents:read` |
| GET | `/documents`, `/documents/{document_id}` | `documents:read` |
| GET | `/documents/{document_id}/intelligence`, `/documents/{document_id}/similar` | `documents:read` |
| GET | `/entities`, `/entities/{entity_id}`, `/entities/{entity_id}/documents` | `documents:read` |
| GET | `/events`, `/events/{event_id}` | `events:read` |
| GET | `/search` | `documents:read` |
| POST | `/documents/{document_id}/verify`, `/security/verify` | `security:verify` |
| GET | `/security/me` | authenticated |
| GET | `/security/audit` | `audit:read` |

`/health`, `/ready`, `/api/v1/system/info`, local OpenAPI/docs and local `/metrics` are system endpoints. Existing asset boundary remains reserved. Secured ingestion retains MIME/size checks; the security request-body budget may be smaller than ingestion's outer maximum. Administrators and source managers have ingestion-write scope; analysts/viewers cannot ingest. Roles bound allowed scopes; product handlers do not hard-code role names. Production requires external trusted OIDC configuration and forbids development identity.

Source creation, ingestion submission, authentication/authorization decisions, integrity and signature checks produce allowlisted audit records. Compose persists them in PostgreSQL and uses Redis rate limiting. JWTs, private keys and raw sensitive payloads are excluded from audit fields.

`as_of` uses analysis/event `available_at`, document persistence `created_at`, and media/entity creation times where applicable; never article publication time. There is no claim of complete historical reconstruction of later edits to mutable registry records or link associations.

## Frontend state

The Docker dashboard starts in real mode. It loads actual feed/detail/intelligence, entity views, events, search, source registry, authorized audit history and live verification. Admin/source-manager scopes enable source creation and ingestion, with server workflow status. Missing permissions or capabilities produce explicit states. A development/OIDC bearer token is entered in the shell and kept in memory; identity changes clear the query cache. Mock mode remains visibly fictional and never supplies real-mode fallback success.

The UI displays recent audit history. API audit pagination supports older records. Feed integrity starts unverified; current verification updates the document card. Feed-wide verified/failed filtering reports unavailable. Similarity is API-only. A production OIDC redirect/refresh flow and source editing are deferred. Generated frontend types are rebuilt from exported backend schemas, including nullable/default-field differences; no backend types were hand-copied.

## Exact local acceptance commands (PowerShell)

Run from the integration worktree. Docker Desktop must be running. The supplied environment file uses alternate ports and an isolated project name to avoid other local projects.

```powershell
docker compose --env-file infrastructure/mvp.env.example -p aegis-integration --profile full up --build -d --wait
docker compose --env-file infrastructure/mvp.env.example -p aegis-integration exec -T api python scripts/mvp_acceptance.py
```

The second command creates a source, seeds curated synthetic identities, submits five historical synthetic articles including media, waits for actual Temporal completion, checks retry identity, raw bytes, analyses/materializations, search/similarity, historical filtering, signatures and AES archive decryption, confirms viewer denial, tampers with a synthetic raw object, verifies failure, restores the bytes in `finally`, verifies success, and checks audit/metrics. It prints a JSON report without tokens. The original synthetic samples in `data/samples/mvp.json` and generated text attachment are CC0; no copyrighted article dumps are included.

Open `http://localhost:23000`. Obtain a five-minute local token using the following command and paste it into the dashboard's Access token field. Change `admin` to `analyst` or `viewer` to demonstrate insufficient write permissions. This is explicit offline development identity, not a production issuer.

```powershell
docker compose --env-file infrastructure/mvp.env.example -p aegis-integration exec -T api python scripts/security_dev.py token --key-id local --role admin --subject local-demo
```

For the automated real browser scenario, install the locked frontend and browser, then hold tokens only in process environment:

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd --filter @aegisnews/web exec playwright install chromium
$env:AEGIS_E2E_TOKEN = (docker compose --env-file infrastructure/mvp.env.example -p aegis-integration exec -T api python scripts/security_dev.py token --key-id local --role admin --subject browser-demo).Trim()
$env:AEGIS_E2E_VIEWER_TOKEN = (docker compose --env-file infrastructure/mvp.env.example -p aegis-integration exec -T api python scripts/security_dev.py token --key-id local --role viewer --subject browser-viewer).Trim()
$env:AEGIS_E2E_EXTERNAL_SERVER = '1'
$env:AEGIS_LIVE_E2E = '1'
$env:AEGIS_E2E_BASE_URL = 'http://127.0.0.1:23000'
$env:AEGIS_E2E_API_URL = 'http://127.0.0.1:28000'
pnpm.cmd --filter @aegisnews/web exec playwright test e2e/live.spec.ts
```

The live test disables trace capture to avoid token artifacts. It proves real feed/detail, model metadata, verification, entity evidence, events, search, audit, source creation, article submission through completion, viewer denial and sign-out. `pnpm.cmd web:test:e2e` without the live/external environment flags runs the independent mock suite.

To stop only this project's services while retaining local data:

```powershell
docker compose --env-file infrastructure/mvp.env.example -p aegis-integration down
```

## Topology and observability

Core: API, web, PostgreSQL/pgvector/pg_trgm, Redis, MinIO, migration/storage/key initializers. Full additionally runs Temporal, worker, Prometheus, Grafana, Loki, Alloy and the OTel collector. There is no Kubernetes, OpenSearch or mandatory Kafka. Full Compose uses offline AI and explicit local security; production settings remain external.

Alternate-port endpoints: API `28000`, dashboard `23000`, Temporal UI `28233`, MinIO console `29001`, Prometheus `29090`, Grafana `23001`, Loki `23100`, OTLP `24318`. The supplied Grafana credentials are the existing local-only `aegis_dev` / `aegis_dev_only`. Structured worker/API logs share the log volume and reach Loki. Request/correlation IDs are retained; Temporal tracing interceptors propagate OTel context from API through workflow/activity boundaries. Metrics use bounded route/method/status labels.

## Validation evidence (2026-10-03)

| Category | Executed result |
|---|---|
| Backend formatting/lint | Ruff clean |
| Strict typing | mypy clean, 90 source files |
| Backend tests, all local switches enabled | 232 passed, no skips |
| Breakdown | 75 unit, 91 contract, 34 security, 16 ingestion, 15 integration, 1 API/web E2E |
| PostgreSQL / MinIO / Redis | Real services exercised, transactional/retry/tamper tests passed |
| Temporal | Complete real workflow, submission identity, retries, terminal validation and original ingestion scenarios passed |
| Migrations | Fresh upgrade, two safe scratch downgrade/re-upgrade paths, metadata checks passed |
| Frontend unit tests | 12 passed |
| Frontend lint/typecheck | Passed |
| Production build | Local and Docker builds passed |
| OpenAPI / JSON / TypeScript drift | Passed |
| Playwright | 10 mock tests and 1 live full-stack test passed |
| Full Compose | All runtime services started; initializers exited successfully |
| Acceptance script | 22 checks passed for five articles, including denial/tampering/restoration |
| Observability | Prometheus target up, Grafana DB healthy, worker records present in Loki |
| Dependency audits | Python and pnpm production audits: no known vulnerabilities |
| Secret scanning | Repository guard and gitleaks integration-history scan passed; no development keys committed |

Independent review found four material issues: latest-run retry selection, earlier-run verification coverage, event cutoff leakage, and media verification coverage. All were fixed; the two-run/media regression was observed failing before the fix and passing afterward. Full backend validation passed afterward. Review was static and is not a production security certification.

One existing Starlette TestClient/httpx deprecation warning remains; no dependency change was needed. Windows local execution required accessible pytest temporary directories and IPv4 service URLs. Initial setup/build/test failures were resolved; no failed check is represented as a pass.

Normal CI remains CPU-only with the offline profile, public package sources and no cloud credentials/model downloads. Database CI now exercises the combined seams. Full Docker/API/browser acceptance is available through a manually triggered workflow; that remote GitHub Actions run was not executed during local integration.

## Limitations and intentionally deferred work

- Offline inference is a deterministic demonstration baseline, not calibrated intelligence. Light/full model installation and quality/performance validation remain external.
- Resolver candidates are curated and bounded to 1,000; no automatic entity creation, full entity master-data UI, event clustering or automatic event revision reconciliation.
- Immutable reanalysis and lineage are supported internally with distinct run keys; there is no dedicated product reanalysis API/UI.
- Exact pgvector similarity and eager dashboard composition are adequate for small local datasets; indexing and batched read optimization are deferred.
- No complete backtesting/historical reconstruction, production identity provider, KMS adapter, external source crawling, source editing, or distributed broker delivery was introduced.
- Local file keys/nonce state and Temporal dev server are explicit development adapters. Production hardening and deployment are outside this integration.

The branch is suitable for review/merge as the requested local MVP once repository owners accept these stated limitations. It is not a production-deployment readiness claim. Do not merge main or push automatically.
