# Agent 1 handoff

Branch: `feat/ingestion-normalization`.
Base: `0203ae95aa1fdf75dd05862c404b5cc743a01f55`.
Worktree: `data/ingestion-worktree` inside the original checkout's ignored data directory.
No merge or push. Frozen domain/event contracts and migrations 0001/0002 are unchanged.

## Delivered behavior

NewsIngestionWorkflow schedules prepare, normalize and commit activities. Prepare validates/hashes/stores raw bytes and media, then persists ingestion and resumability state. Normalize verifies raw SHA-256 and creates canonical values. Commit atomically inserts document, MediaAssets, explicit DocumentMediaLinks, document.ingested.v1 and document.normalized.v1 outbox envelopes. All external work runs in activities; PostgreSQL calls run off the async worker loop. Activity retries are bounded to five attempts; invalid inputs and conflicts are terminal.

Manual/local text, HTML, article JSON, local PNG/JPEG/PDF/text attachments, JSONL historical records and JSON arrays are supported. Source registration/retrieval, ingestion single/batch submission, workflow polling and canonical retrieval use existing API envelopes. API does not accept worker paths or fetch URLs. Exact endpoint/request/demo details are in [ingestion.md](ingestion.md).

Canonical retry identity is source_id + idempotency_key. A complete semantic request fingerprint distinguishes conflicting requests; correlation IDs are excluded. DB advisory locks serialize initial persistence, journal row locks serialize completion, and outbox staging is atomic. Different keys intentionally yield different documents, sharing raw objects when bytes/MIME match. Object keys are content-addressed and contain no unsafe user paths. Object writes surviving DB failure are verified and reused on retry; pending ingestions retain metadata/IDs/references in the journal. Cleanup requires quiescing writers and checking all RawObject references; no automatic destructive sweeper is added.

Normalization preserves publisher timestamps and known observation times, keeps unknown language/publication time null, removes HTML scripts/styles, normalizes whitespace/line endings, and starts revision at 1. Local first_seen uses a durable replay-safe workflow start time by default; persistence and creation clocks remain separate.

Migration: **ingestion_0001**, down_revision **0002_contract_hardening**. Only ingestion_journal is added. Alembic metadata imports that private model. Reconcile any parallel branch migration heads during integration; this branch does not assume another agent's migration exists.

## Verification performed

- Full suite with isolated PostgreSQL, local Temporal execution enabled for ingestion acceptance, and live MinIO acceptance: **154 passed, 12 skipped**, one pre-existing Starlette/httpx deprecation warning.
- Explicit real Temporal retry/terminal-validation suite: **2 passed** (the SDK local-server test is opt-in in the full suite).
- Ruff lint and format checks passed; strict mypy passed for 57 source files; generated schema drift and git whitespace checks passed.
- New journal migration upgrade/downgrade/upgrade and Alembic metadata comparison passed against PostgreSQL.
- Live MinIO + Temporal + PostgreSQL + API acceptance passed: preserved exact raw bytes, created canonical document, linked attachment, staged two outbox events, retrieved document through API.
- Tests also cover concurrency, duplicate/conflicting ingestion, object-write/DB-failure recovery, failed-outbox rollback, image association, original times, source API persistence, batch import, body budgets, invalid content and submission/status identities.

The test services were isolated local processes and disposable schemas/buckets, not modifications to shared production infrastructure. MinIO was built from the exact pinned source/checksum already used by the repository's Dockerfile because no Docker daemon was running. No test requires paid APIs.

## Limitations and integration notes

The complete foundation migration chain was not roundtripped locally: installed PostgreSQL lacks pgvector. Run scripts/verify_migrations.py using the existing pgvector Compose/CI service. The journal migration itself was exercised against real PostgreSQL. Foundation service integration and E2E tests remain opt-in; one separate Temporal test was run explicitly.

Development payloads are bounded: article/media 256KiB each, complete request 768KiB, HTTP body 4MiB, API batch 20 items, offline dataset 16MiB. PNG/JPEG/PDF checks screen MIME signatures; no deep file decoder, malware scanner or CV is added. HTML parser is conservative fixture extraction, not a browser rendering engine. JSON-array raw objects preserve deterministically serialized records rather than aggregate file formatting. Batch submission/import can partially finish and is resumed by replaying the same immutable input. Cleanup is operational, document corrections/revisions are outside this branch, and authentication remains Agent 3's integration work. Temporal request history contains bounded raw source material; configure retention appropriately. The existing worker task queue and FoundationWorkflow remain compatible.

## Files changed

```text
aegis/ingestion/cli.py
aegis/ingestion/http.py
aegis/ingestion/importers.py
aegis/ingestion/inputs.py
aegis/ingestion/repository.py
aegis/ingestion/runtime.py
aegis/ingestion/service.py
aegis/ingestion/submissions.py
aegis/normalization/article.py
apps/api/main.py
apps/api/routes/ingestions.py
apps/worker/main.py
apps/worker/workflows.py
apps/worker/ingestion_activities.py
docs/api-contracts.md
docs/ingestion.md
docs/ingestion-handoff.md
docs/superpowers/plans/2026-10-03-ingestion-normalization.md
migrations/env.py
migrations/versions/ingestion_0001.py
schemas/openapi/v1.json
tests/fixtures/ingestion/article.html
tests/fixtures/ingestion/evidence.txt
tests/fixtures/ingestion/history.jsonl
tests/ingestion/test_pipeline.py
tests/integration/test_foundation.py
tests/unit/test_api.py
tests/unit/test_ingestion_api.py
tests/unit/test_ingestion_importers.py
tests/unit/test_ingestion_normalization.py
tests/unit/test_ingestion_workflow.py
```
