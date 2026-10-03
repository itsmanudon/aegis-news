# MVP Integration Implementation Plan

**Goal:** Integrate the four completed branches on the exact frozen base without changing canonical contracts.

**Architecture:** Preserve ingestion's workflow and repository, call AI providers from retryable activities, persist immutable analyses and derived records transactionally, and sign actual lineage using the security provider. Product routes compose these records for the existing dashboard.

**Execution:** Inline under the user's explicit integration instructions; no additional design approval is needed.

**Constraints:** Offline CPU baseline, optional local models, PostgreSQL source of truth, explicit media links, event revisions, local Compose, no pushes or main changes.

## Tasks and validation

- [x] Create isolated worktree at frozen base; integrate ingestion, AI (including prerequisite c7f0af6), security, frontend. Resolve API composition by retaining both owners' behavior.
- [x] Add `migrations/versions/mvp_merge_0001.py` with both independent heads; run `scripts/verify_migrations.py` against a fresh scratch database.
- [x] Add `aegis/intelligence/pipeline.py` and worker integration activities: deterministic retry identities, append analyses, materialize mentions/events, preserve resolution lineage, sign raw/document/analysis/derived records, stage outbox in the same transaction. Test retries, unsupported models, tampering and rollback.
- [x] Add product query service/routes with canonical envelopes, cursor pagination and availability cutoffs; scope all ingestion/read routes; persist local audit records. Test anonymous, analyst and admin requests.
- [x] Generate OpenAPI/JSON and TypeScript contracts, connect existing frontend adapter/auth shell to real endpoints, expose authorized source/ingestion operations. Test real transport without mock success.
- [x] Add safe synthetic demo, isolated full Compose, shared generated development keys and offline configuration. Execute Temporal and browser acceptance including denial/tampering.
- [x] Run lint/format/mypy, all backend tests, migration roundtrips, frontend lint/types/build/unit/Playwright, schema drift and dependency audits. Record executed results and limitations.
- [x] Independent final review; fix material findings. Commit focused changes and verify the final clean worktree before reporting. No main merge or push.

## Review focus

Retries must not create duplicate analyses or outbox events; reruns must use new analysis identities. Unresolved mentions must not create canonical entities. Availability cutoffs must never use publication dates. A valid signature alone must not conceal changed database or object bytes. Optional model failures must not prevent normalized document ingestion.

## Integration ledger

- Worktree: `.worktrees/integration-mvp`, branch `integration/mvp`, base `0203ae95aa1fdf75dd05862c404b5cc743a01f55`.
- AI tip-only application was aborted when missing prerequisite files showed that the branch contained two commits; both commits then applied cleanly.
- Security conflict: `apps/api/main.py` imports, lifespan cleanup, CORS/middleware and router registration combined according to ingestion/security ownership.
- Docker requires sandbox escalation; existing unrelated services occupy standard ports, so validation uses a distinct Compose project and ports.
- Frozen contracts remain intact. Document historical availability uses persistence `created_at`, because the frozen document contract has no `available_at`; analysis/event queries use their explicit availability clocks. Publication time is never a knowledge cutoff. Mutable registry/link history remains a documented limitation.
- Embeddings remain immutable typed analysis output, cast to pgvector for bounded cosine ranking. This avoids a duplicate embedding store/migration; the tradeoff is an exact scan, unsuitable for large production corpora without indexing work.
- Missing optional model artifacts and no predictions return an explicit unavailable activity result. They do not create fabricated empty analyses or prevent normalized document ingestion. Operational persistence failures still retry/fail normally.
- Independent static review found latest-run provenance retry selection, incomplete earlier-run coverage, future-event cutoff leakage and unsigned media content. All four were fixed. A two-run/media regression failed before the fix and passed afterward; all 232 backend tests then passed with real infrastructure and no skips.
- Final validation: Ruff/strict mypy, 232 backend tests, migration/metadata roundtrips, 12 frontend unit tests, lint/types/local and Docker production builds, generated-schema drift, 10 mock browser tests, live browser acceptance and 22 Docker acceptance checks passed. Production dependency audits and secret guard passed. Remote GitHub Actions and optional heavy model profiles were not executed.
- Exact commands, endpoint inventory, topology, evidence and remaining limitations are recorded in `docs/mvp-integration.md`.
