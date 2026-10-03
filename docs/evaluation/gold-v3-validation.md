# Gold v3 Human validation ledger

Date: 2026-10-03. Branch: `eval/human-review-light-models`.
Main base `3c563a72a1c80fe50fe1fbdad25e69e8e7dfac0c`; working base
`175d71b188bcde06bd7730e20ea14b3235753756`. No main merge/rebase/tag change.

| Check | Executed result |
|---|---|
| Human-review completion | 16/16 reviewed; zero pending, zero human label changes; one reviewer |
| Dataset/source integrity | Unique IDs, unchanged documents, exact valid offsets, current/original labels and change logs checked; historical v1/v2 manifest passed |
| Gold v3 manifest | Exact UTF-8/LF SHA-256 and byte sizes verified; 16 cases, 17 mentions, 12 events, 2 media |
| Offline Gold v3 quality | Fresh completed 16-sample pass; same scorer; also ran successfully in ordinary environment without optional torch/models |
| Light CPU Gold v3 quality | Fresh whole-profile valid pass; all pinned pretrained models available |
| Light GPU Gold v3 quality | Fresh whole-profile valid pass; CUDA detected/executed; same model revisions/specs except device |
| CPU/GPU consistency | Exact categorical outputs/metrics/top-three rankings; maximum absolute numeric difference 6.332993507385254e-6, below 1e-5 |
| Performance | Each profile: cold document + full unmeasured warmup + 48 measured sequential seven-task passes; GPU synchronized; RSS/PyTorch VRAM stats recorded |
| Artifact/hardware receipt | All cached selected model hashes/bytes matched historical receipt; 964,224,182 bytes selected payload; no new model downloads |
| Final real Temporal pipeline | Six fresh five-document batches across three profiles; 30 documents, 180 immutable analyses; signatures verified, media linked, duplicates stable; no running workflows at end |
| Evaluation seam suite | 25 passed: pending/duplicate/document/offset/snapshot/log mismatches, legitimate logged changes, manifest tamper, p95, device specs and stale worker pollers |
| Unit + contract suite | 196 passed, 1 skipped (4.58 s); existing security/crypto/analysis/provider/contract checks included |
| Ruff format/lint | Passed, 207 files checked at final validation |
| Strict mypy | Windows and Linux-platform checks passed, 105 source files |
| Backend OpenAPI/JSON schema drift | Passed; no exported contract changes |
| Frontend generated types + typecheck | pnpm.cmd web:api:check and web:typecheck passed; frontend implementation untouched |
| Secret guard | Passed on tracked and nonignored untracked files; environments/model caches/keys excluded |
| Presentation | Comparison generated from final reports; sentiment figure visually inspected |
| Cleanup | Evaluation containers/network stopped without deleting volumes/keys/counters; unrelated Docker projects preserved |

Normal CI configuration/dependencies remain offline, CPU-safe and free of mandatory
models/CUDA/downloads. CUDA tooling is optional/local. No hosted CI was triggered in
this phase; browser E2E, full frontend production build, all infrastructure tests,
dependency audits and a standalone Gitleaks run were not repeated. The actual pipeline
runs exercise storage/SQL/Temporal/provenance and the clean stack migrated to head,
but no new downgrade/migration requalification is claimed.

## Attempts and limitations

- Initial data validation found Harbor Council and Copper Basin pending; no label/status
  was fabricated. The user marked both reviewed before metadata was finalized.
- First selected pytest invocation: 23 passed, 2 setup errors from sandbox-denied system
  temporary storage. Rerun with a new ignored workspace basetemp passed all 25. Final
  broader unit/contract invocation passed 196 with one skip.
- PowerShell blocked the pnpm.ps1 shim; using pnpm.cmd passed without changing execution
  policy. A documentation-writing here-string initially failed PowerShell parsing; no
  file was written by that attempt, and the document was added through the patch tool.
- Routine line-length/zip lint findings were corrected; final format/lint/mypy reran.
- Initial Offline/CPU pipeline reports are retained with `-initial` suffix. The old stack
  exported telemetry to an absent collector. A GPU attempt aborted on one HTTP 401 during
  workflow polling; 20 later probes passed and the cause is unconfirmed. Authentication
  was not relaxed. Recovery was attempted, but not qualified as GPU timing evidence.
- Final pipeline comparison used fresh `aegis-gold-v3` volumes/keys/Temporal history,
  IPv4 loopback, and consistently disabled telemetry export. No pending workflows
  remained. Local key state was copied once to a new ignored worker directory and
  retained; it must never be overwritten/restored onto a used AES key. The benchmark
  uses one encryption writer; copied allocators are not safe for multiple writers.
- Existing Starlette/httpx deprecation warning remains. One human, 16 synthetic CC0
  English items, organization-heavy NER and incomplete retrieval judgments limit quality
  claims. There is no real-world held-out corpus/drift study. No Full profile was run.
- GPU utilization was not isolated from display/background applications; no attributable
  percentage claimed. RSS is sampled, VRAM is PyTorch allocator memory. CUDA setup/import
  is separately measured before the cold document. No downloads/install in timing.

[Final results and exact model/runtime details](gold-v3-gpu.md),
[reproduction](gold-v3-reproduce.md), [presentation tables](evidence/gold-v3/comparison.md).

## Final reconciliation checks (2026-10-04)

The evaluation delta was reviewed from main `3c563a7` through `e877d9c`;
it contains evaluation/review/benchmark evidence and supporting tools, without product
expansion. Historical datasets/manifests and both existing release tags are preserved.
The existing `v0.2.0-evaluation` tag identifies the earlier Phase 6 release, not Gold v3.

GNU make is unavailable on this Windows host. Every `make check` recipe was executed
directly using `uv` and `pnpm.cmd`; frontend build used `NEXT_TELEMETRY_DISABLED=1`.
Ruff format/lint (207 files), strict mypy (105 sources), schema export drift, generated
TypeScript drift, frontend lint/typecheck/build, and 12 frontend unit tests passed.
The ordinary backend run passed 228 tests with 36 service-dependent skips. With the
full local services and a separate disposable database, 260 passed and 4 skipped.
The live Playwright flow passed against the real API; the mock suite passed 10 flows
with 2 opt-in live/evidence skips. No expensive pretrained benchmark was repeated.

`scripts.validate_gold_v3` verified all review blocks and v2/v3 manifest hashes;
a fresh Offline evaluation completed in the ordinary environment. The secret guard
passed, and Gitleaks v8.24.2 scanned 31 commits without leaks. The supported migration
verifier passed upgrade/check/downgrade/re-upgrade sequences in its owned scratch database.
The supported full demo start/seed reused existing volumes/data and confirmed duplicate
stability and provenance verification. No demo reset or volume deletion was performed.

Two initial test attempts inherited local `.env` settings: the CORS unit test expected
port 3000 while the demo origin was 33000, and one infrastructure test inherited an old
Temporal port. Explicit test CORS and both Temporal address variables resolved these
environment mismatches; no application/security logic was changed. The existing
Starlette/httpx deprecation warning remains. Windows denied deleting `.pytest_cache`;
it remains ignored, and pytest was rerun without its cache plugin. Accessible static
caches and old benchmark logs were removed. Useful environments, key/nonce state,
model caches and checked-in evaluation evidence were retained. Coverage/Hugging Face
cache exclusions and private-key build-context exclusions were added.

Hosted branch/main CI and final reconciliation identifiers are reported at handoff;
this local ledger does not assert hosted success before those runs finish.
