# Offline ingestion and normalization

This branch implements the Agent 1 mission against base `0203ae95aa1fdf75dd05862c404b5cc743a01f55`. Frozen Source, RawIngestion, NewsDocument, MediaAsset, DocumentMediaLink and event contracts are unchanged. The sole schema addition is private `ingestion_journal`, migration `ingestion_0001` from `0002_contract_hardening`.

## Local acceptance demo

From this worktree, start the existing full Compose profile with ingestion enabled:

```sh
AEGIS_TEMPORAL_ENABLED=true docker compose --profile full up --build -d --wait
uv run python -m aegis.ingestion.cli source --name "Offline archive" --kind upload
# Substitute the returned src_ identifier below.
uv run python -m aegis.ingestion.cli local tests/fixtures/ingestion/article.html --source-id src_UUID --key article-v1 --media tests/fixtures/ingestion/evidence.txt --wait
uv run python -m aegis.ingestion.cli historical tests/fixtures/ingestion/history.jsonl --source-id src_UUID --key history-v1 --wait
curl http://localhost:8000/api/v1/documents/doc_UUID
curl http://localhost:8000/api/v1/ingestions/ing_UUID
```

On PowerShell set `$env:AEGIS_TEMPORAL_ENABLED='true'` before running Compose. The CLI reads files on its own machine and sends bounded bytes to Temporal. API and worker never accept filesystem paths or fetch source URLs. CLI `--wait` prints workflow, ingestion and document IDs. Repeating a command with the same source/key/bytes/metadata returns the same canonical records.

The sample history is synthetic, openly reusable fixture material. JSONL streams one article object per physical line and preserves each line's original bytes without its line terminator. A JSON array importer serializes each article deterministically as its raw record; it does not upload the original aggregate file. Keep that dataset file externally if aggregate formatting matters. Dataset identity is `<dataset-key>:<one-based-physical-line-or-array-index>`; blank JSONL lines are skipped without renumbering. Dataset keys must identify immutable versions: reordering or editing a record under an existing key is a conflict. CLI imports can partially finish before a later invalid record; retry an unchanged file to continue safely.

## Request and endpoints

All endpoints use the existing v1 response/error envelopes. POST ingestion returns HTTP 202 and `data.workflow_id`. Poll the run endpoint for completion and its `result.ingestion_id` / `result.document_id`, then retrieve canonical records. A run that fails validation/conflict has status FAILED; inputs are not copied into public exception messages. Submission acceptance does not imply canonical persistence.

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/v1/sources` | Create Source from name, kind and optional HTTP(S) URL |
| GET | `/api/v1/sources/{source_id}` | Retrieve Source |
| POST | `/api/v1/ingestions` | Submit one durable workflow |
| POST | `/api/v1/ingestions/batch` | Submit `{"items": [...]}` with up to 20 independent requests |
| GET | `/api/v1/ingestion-runs/{workflow_id}` | Temporal status and completed result IDs |
| GET | `/api/v1/ingestions/{ingestion_id}` | Retrieve canonical RawIngestion including object reference |
| GET | `/api/v1/documents/{document_id}` | Retrieve canonical NewsDocument |

Example request (`content_base64` represents `Title\nBody`):

```json
{
  "source_id": "src_00000000-0000-4000-8000-000000000001",
  "idempotency_key": "article-v1",
  "content_type": "text/plain",
  "content_base64": "VGl0bGUKQm9keQ==",
  "media": [
    {"kind": "attachment", "content_type": "text/plain", "content_base64": "ZXZpZGVuY2U="}
  ]
}
```

Optional metadata: title, language, published_at, first_seen_at, source_url, correlation_id. Article JSON accepts exactly title, text, optional language and published_at. Explicit request metadata takes precedence. source_url and Source.url are metadata only. Temporal-disabled API submission returns SOURCE_UNAVAILABLE. Each batch validates all inputs before starting workflows, but Temporal submission is not a distributed atomic batch. A connection failure can accept a prefix of the batch: retry the same batch.

## Workflow and transaction boundaries

`NewsIngestionWorkflow` deterministically schedules three activities:

1. **prepare_ingestion:** acquire inline bytes; enforce structured/type/size checks; parse for validity; compute SHA-256 and request fingerprint; check Source/retry; write raw/media objects; persist RawObject references, RawIngestion and journal together.
2. **normalize_ingestion:** load durable journal and raw object; check raw SHA-256; extract canonical document values, using the journal's reserved document ID.
3. **commit_ingestion:** lock the journal row; persist NewsDocument, MediaAsset occurrences, explicit DocumentMediaLink rows and both frozen outbox envelopes in one PostgreSQL transaction. Return original document on a retry after commit.

StoreRaw/PersistIngestion are combined in one independently retryable activity. PersistDocument/AssociateMedia/StageOutboxEvents share one activity because their writes must commit together. No I/O, random IDs, parsing, or system clocks run in workflow code. The workflow's replay-safe `workflow.now()` supplies default observation time. UUID4 IDs, persistence clocks, storage and DB work occur in activities. PostgreSQL calls run in threads so the worker event loop stays responsive.

Activities have five attempts, exponential 1s backoff capped at 30s. Prepare has a 60s attempt / 5min overall activity budget; normalize and commit have 30s attempt / 3min budgets. The workflow execution limit is 15min. Validation, missing source and integrity/idempotency ValueErrors become terminal InvalidIngestion errors; infrastructure failures retry. After exhaustion, resubmit the identical request once infrastructure is repaired. Temporal allows a new run after failure and uses an existing concurrent run; completed requests are returned without re-execution while retained. DB idempotency remains authoritative after Temporal history retention expires.

## Normalization and time semantics

UTF-8 (optional BOM) is required. CRLF/CR become LF; surrounding whitespace is trimmed. Plain text uses its first line as title, limited to 512 characters, and keeps that line in body text. HTML decodes entities, extracts title and html lang, separates common block tags, and excludes script/style/noscript content. HTML remains text; no executable HTML is returned. JSON uses validated article metadata. Unknown language remains null; no language model or heuristic guess is used. Empty bodies, binary NULs, malformed UTF-8/JSON, naive dates and unsupported MIME declarations are rejected.

`published_at` is nullable publisher metadata, including future publisher claims; it is never replaced with local ingestion time. `first_seen_at` uses an explicit known observation when supplied, otherwise workflow start (or service entry for direct callers), before object writes. Future local observations are rejected. `ingested_at` is assigned when durable raw references and ingestion are persisted. `created_at` is document creation during normalization and cannot precede ingestion. The first successfully committed document retains its timestamps on all duplicate completions. Revision starts at 1; this branch does not implement document revisions or corrections.

## Exact idempotency

The canonical retry identity is **(source_id, idempotency_key)**, enforced by the existing ingestion unique constraint. A SHA-256 request fingerprint includes decoded raw bytes, MIME, source/key, explicit title/language/times/source_url, and ordered media kinds/MIME/content hashes. Correlation ID is excluded. Omitted/default fields normalize through Pydantic; equivalent instants with different timezone representations may still be distinct request fingerprints, so replay the same submitted metadata.

Identical identity/fingerprint returns the original ingestion and reserved document ID. Different fingerprint under an existing identity raises conflict and never changes committed records. Identical bytes under different keys or sources intentionally create distinct ingestions/documents while sharing immutable raw objects. Media identity is by ordered attachment occurrence within an ingestion: duplicate supplied attachments can create separate MediaAssets sharing one raw object. Associations always use document_media rows.

Transaction advisory locks serialize source/key persistence, and per-object locks prevent concurrent duplicate RawObject rows. Journal row locks serialize document completion. Existing outbox uniqueness plus the completion transaction guarantees exactly two staged envelopes per created document (`document.ingested.v1`, `document.normalized.v1`), not exactly-once external delivery. No dispatcher or broker is added.

## Object storage and recovery

The existing ObjectStorage abstraction and S3ObjectStorage adapter are used with MinIO. Keys contain only fixed prefixes, SHA-256 bytes and a MIME digest:

`ingestion/v1/{raw|media}/{hash-prefix}/{content-sha256}/{mime-digest}`

No user paths, URLs, titles or filenames enter keys. MIME is part of the location so identical bytes with different MIME declarations cannot overwrite metadata. Duplicate writes reuse existing content after verifying bytes/hash/size/MIME. Concurrent writers can write the same immutable bytes safely. A corrupt existing object stops processing instead of being silently replaced.

There is no PostgreSQL/S3 distributed transaction. If object storage succeeds and DB persistence fails, objects remain under deterministic keys, and identical retries verify/reuse them. If the ingestion commits and normalization/completion fails, the journal retains original metadata, object references, reserved IDs and correlation ID; replaying the same request resumes without duplicating ingestion. A completion failure rolls back document/media/link/outbox writes together. Do not delete objects as a per-request compensation: another ingestion can share them.

Orphan cleanup is an operator procedure, not an automatic sweeper: stop submissions and workers, wait for active activities to finish and all retries to stop; snapshot/inventory only `ingestion/v1/`; compare each bucket/key against **all raw_objects**, including media objects held by pending journals. Retain referenced objects. Retain unreferenced candidates at least 24h and through the entire retry/recovery window; archive a candidate manifest before deleting. Recheck references immediately before deleting while writers remain stopped. Resume ingestion afterward. Object lifecycle rules must not expire referenced/pending data. An object inventory age alone cannot establish that a live write is orphaned. This branch intentionally provides recovery by retry and a cleanup strategy rather than a concurrent destructive sweeper.

## Security and limits

Article and each media item: 256KiB decoded; up to four media items, with a 768KiB total serialized request budget for Temporal. API body limit: 4MiB before JSON parsing, batch: at most 20; offline dataset: 16MiB. Supported article types: text/plain, text/html, application/json. Images: PNG/JPEG magic headers; attachments: PDF header or validated UTF-8 text. Signature checks are MIME screening, not full image/PDF decoding or malware scanning. No remote fetcher, OAuth/RBAC, CV, cryptography or financial endpoints are introduced. These bounded development endpoints need Agent 3's access-control work before production exposure. Raw source material is preserved in S3 and in bounded Temporal request history; retention/privacy configuration remains deployment work.

## Tests and integration

```sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python -m scripts.export_schemas --check
# Disposable PostgreSQL: tests use isolated schemas and remove those schemas afterward.
AEGIS_INGESTION_TEST_DATABASE_URL=postgresql+psycopg://... uv run pytest -q tests/ingestion
# SDK local server execution and real activity/API test:
AEGIS_RUN_INTEGRATION=1 uv run pytest -q tests/unit/test_ingestion_workflow.py
AEGIS_INGESTION_TEST_DATABASE_URL=postgresql+psycopg://... AEGIS_INGESTION_TEST_TEMPORAL=1 uv run pytest -q tests/ingestion
# Live acceptance uses unique disposable bucket, MinIO's documented local dev credentials.
AEGIS_INGESTION_TEST_DATABASE_URL=postgresql+psycopg://... AEGIS_INGESTION_TEST_MINIO=http://localhost:9000 uv run pytest -q tests/ingestion/test_pipeline.py::test_live_minio_temporal_acceptance
```

SDK local-server tests may download the free Temporal development executable on first run. Production integration uses the existing Compose service. The journal migration is imported by Alembic metadata; 0001 and 0002 are untouched. Reconcile parallel migration heads at integration time, without rewriting those base migrations. Generated OpenAPI is updated; domain and event schemas are unchanged. Existing foundation smoke workflow stays registered for compatibility. The worker uses the existing configured task queue.

Temporal retry and determinism choices follow the [official Python SDK guidance](https://github.com/temporalio/sdk-python) and [activity error-handling documentation](https://docs.temporal.io/develop/python/failure-detection).
