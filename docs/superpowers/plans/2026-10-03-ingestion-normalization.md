# Ingestion normalization implementation plan

**Goal:** Implement the supplied Agent 1 mission against base 0203ae95aa1fdf75dd05862c404b5cc743a01f55 without changing frozen domain contracts.

**Architecture:** Bounded inline/local inputs enter Temporal. Activities validate, hash, preserve objects, persist a resumable ingestion journal, normalize, and atomically persist document/media/outbox. PostgreSQL serializes retries by source/key; MinIO writes use safe deterministic keys.

**Execution:** Native implementation in this isolated worktree, as authorized by the mission. No merge or push. The supplied mission is the specification; no architecture redesign or additional approval gate.

## Tasks

- [x] Input and normalization: add structured bounded requests, UTF-8/JSON/HTML parsing, MIME signatures, metadata/time validation, JSON/JSONL and local importers. Test invalid bytes, empty content, timestamps, scripts and unsafe paths first.
- [x] Persistence and recovery: add ingestion journal model/migration `ingestion_0001` from `0002_contract_hardening`; implement Source service, immutable ingestion creation, request fingerprint conflicts, deterministic raw/media objects, and atomic completion using existing stage_event. Test duplicates, concurrency, failure after object write, media links and outbox rollback.
- [x] Durable orchestration and API: implement NewsIngestionWorkflow with prepare/normalize/commit activities and deliberate retry limits. Add source/ingestion/document endpoints using existing envelopes and an offline CLI. Test activity retries, sandbox execution, API validation and retrieval.
- [x] Verification and documentation: run unit/contract checks, lint/types, and service integration when available; document exact idempotency, bounded inputs, cleanup quiescence, and acceptance demo commands. Commit all branch changes and report evidence and infrastructure limitations.

## Review focus

Conflicting metadata with identical bytes must conflict; concurrent completions must stage only two events; retries must retain first committed times; invalid images must fail before writing; cleanup must never race active storage writes.
