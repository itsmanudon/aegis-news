# Historical corpus load evidence

Local non-commercial development run, 4 October 2026. This is pipeline/UX evidence,
not an AI quality benchmark. Gold v3 remains the reviewed evaluation reference.
See the [loader guide](historical-corpus.md) for rights, commands and resume behavior.

## Input and method

- AG News CSV v3 training split, pinned mirror revision
  `03836ce08fce38daac53e9b4255ef16e0b9f6303`.
- Cached CSV: 120,000 rows, 29,470,338 bytes, SHA-256
  `76a0a2d2f92b286371fe4d4044640910a04a803fdd2538e0f3f29a5c6f6b672e`.
- Stable valid/unique prefix: 3,003 rows considered, 3,000 selected. Exact
  duplicates at ordinals 791, 1687 and 1752 skipped. No balancing claim.
- Source categories: Business 704; Sci/Tech 983; Sports 580; World 733.
  Categories are local source metadata, never classifier inputs/outputs.
- Headline/description article JSON; English; publication timestamps, publishers,
  article URLs and authors unavailable and not fabricated. No media supplied by CSV.
- Existing authenticated batch HTTP API → Temporal → offline worker → normalization,
  analyses/materialization, signed provenance and storage. No direct persistence writes.
- One reused source; batches bounded at 20, two concurrent batches for the full run;
  loader HTTP traffic capped at 12 requests/sec. Existing volumes/demo records retained.
- Shared local Docker host with other workloads; results are not dedicated-machine
  performance measurements or a production load test.

## Measured runs

Counts overlap: completed includes existing; submitted counts accepted work in that run.
The same stable prefix/source/checkpoint was used for every run.

| Run | Requested | Newly submitted | Existing | Completed | Failed | Pending | Seconds | New records/min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Smoke | 10 | 10 | 0 | 10 | 0 | 0 | 13.03 | 46.04 |
| Stability | 100 | 90 | 10 | 100 | 0 | 0 | 82.25 | 65.65 |
| Idempotent rerun | 100 | 0 | 100 | 100 | 0 | 0 | 9.125 | 0 |
| Full prefix (20 × 2 bounded batches) | 3,000 | 2,900 | 100 | 3,000 | 0 | 0 | 4,787.312 | 36.35 |

The 100-item stability run made 377 API requests with zero transport/rate-limit retries;
response median 31 ms and p95 187 ms. The idempotent rerun made 102 requests,
median 16 ms/p95 46 ms, with zero retries and zero new submissions.
The full stage took 79 minutes 47 seconds: 18,719 API calls, zero HTTP retries,
response median 78 ms/p95 500 ms. Temporal activity retries are separate from HTTP
retry counts. All three ingestion stages inserted 3,000 records cumulatively in
4,882.593 seconds (81 minutes 23 seconds, excluding verification/idempotent rerun
and gaps between commands). Workflow completion rate: 100% of selected records.

The full prefix skipped three exact duplicates. Entity extraction/resolution abstained
for 1,041 documents; event extraction for 2,886. Topics, sentiment and embeddings
completed for all 3,000. Successful ingestion does not claim correctness of these outputs.

## Final API and storage verification

- Source: `src_7a2e181e-573f-4f64-8cf8-54189eb2bbf2` (runtime receipt, not a portable
  configuration value; the loader discovers/reuses sources through the API).
- Source-filtered API traversal: 30 cursor pages, **3,000 unique document IDs**.
  Four samples across the ID ordering had 4–5 immutable analyses, 9–11 provenance
  records and valid content/chain/signature verification. Exact-headline search
  returned the target; the similarity endpoint returned three hash-vector neighbors.
- 117 corpus events have `evidence_kind=model_output` and producing analysis IDs.
  The canonical entity register remains four curated records; corpus names stay
  extraction mentions/unresolved output rather than invented resolved entities.
- API readiness passed; container configuration confirmed `AEGIS_AI_PROFILE=offline`.
- Database totals: 3,024 documents (24 pre-existing preserved), 13,176 analyses,
  3,426 entity mentions and 145 events. Database size: 88,587,287 bytes.
  Growth since the **after-10-record** checkpoint (13,638,679 bytes) is 74,948,608
  bytes; this is not an empty-database/pre-load baseline and includes audit/other rows.
- MinIO total: 6,032 objects / 23,861,415 bytes. Growth from an **early during-load**
  checkpoint (264 objects / 981,574 bytes, DB then held 143 documents) is 5,768 objects /
  22,879,841 bytes. Measurements are approximate growth observations, not a controlled
  storage benchmark; PostgreSQL figures do not include the separate WAL volume.

## Verified seams

- 10-item smoke: real browser search → article intelligence → integrity verification →
  entity register → event timeline passed, with no browser JavaScript errors.
- After all 3,000 completed, the maintained browser test passed again: real search,
  document intelligence, verification, entity register, events and **filtered Documents**;
  2.7 seconds browser test time (4.0 seconds total runner). No mock fallback or JavaScript errors.
- 100-item stability: API cursor traversal returned 100 unique documents for the corpus
  source; three sampled documents had analyses and successful provenance verification.
- Authenticated API checks returned embeddings/similar documents, model entity mentions,
  entity register and event records. Unauthenticated document access returned HTTP 401.
- A real activity retry occurred during the full run: ordinal 1368's `analyze_topics`
  first attempt reached the existing 180-second StartToClose timeout. Temporal history
  recorded attempt 2 with that timeout as its previous failure; the same workflow
  completed at 05:28:12 UTC without manual resubmission. The cause of the slow first
  attempt was not established. Zero terminal workflow failures does not mean zero
  activity retries. Intermittent pauses are included in measured elapsed time.
- Another recovered topic attempt rejected `available_at < created_at`. This is
  consistent with a wall-clock regression between timestamp reads; the underlying
  clock cause was not established. The contract was preserved and Temporal retried;
  timestamp validation was not weakened to make the load pass.
- Offline NER/event extraction can abstain. At 100 documents, entity extraction and
  resolution were unavailable for 53 documents and events for 98; topic, sentiment and
  embedding stages completed for all 100. This is degraded baseline behavior, not
  fabricated intelligence. Unresolved names are not promoted to canonical entities.

## Validation

- Backend: Ruff format/lint, strict mypy (106 sources), 239 tests passed / 36 skipped.
  Opt-in database/Temporal tests were not enabled in that test invocation; live loads
  exercise the real workflow separately. One existing Starlette/httpx deprecation warning.
- Loader: 11 unit tests cover conversion, stable keys/limits, malformed/invalid UTF-8
  and duplicate rows, mocked downloads/hash protection, uncertain acknowledgement,
  checkpoint resume, failed workflow rerun and bounded in-flight batches.
- Frontend: lint, typecheck, generated API drift check, production build and 12 unit tests.
- Backend schema drift, repository secret guard and Gold v3 validation passed (16 reviewed,
  zero changes). Gold datasets/model benchmarks were not modified or rerun.

## UX observations

The real client fetches cursor pages but eagerly fetches intelligence for every row before
rendering the complete feed. This can make unfiltered Dashboard/Documents slow and put
pressure on the existing rate limit. Specific searches restrict the work and are the
recommended inspection path. Pagination/summary loading remains a separate future task;
no frontend redesign, mock fallback or security-limit relaxation was introduced here.

Measured after all 3,000 workflows completed: the real Dashboard API connection was
connected, but the full feed failed with `RATE_LIMITED` after 37.62 seconds. It issued
986 intelligence requests (985 HTTP 200, one HTTP 429), receiving 8,460,883 bytes of
intelligence response bodies before rendering any review-queue records. Unfiltered
Documents then showed the same explicit error. **The unfiltered feed did not pass**;
the diagnostic only observed this failure. This is a frontend volume limitation,
not failed ingestion or a reason to weaken the API limit. Specific search/filtered
Documents, details, provenance, entities and events passed the maintained real flow.

Priorities for a separate UX task: use cursor pagination on screen, avoid per-row
eager intelligence loading for the entire workspace, and load bounded dashboard
summaries. The conservative loader also waits for all workflows in each batch;
a single slow activity can hold that batch until its retry finishes.

Raw corpus, converted JSONL, local state and reports are ignored in `.data/historical/`.
Removing local files does not remove server records. The supported demo reset deletes
the entire isolated demo project; it was **not** used during this load.
