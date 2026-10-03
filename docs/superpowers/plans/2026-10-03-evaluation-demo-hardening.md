# Evaluation and Demo Hardening Implementation Plan

> Use superpowers:executing-plans inline, with one independent final branch review.

**Goal:** Make the frozen local MVP measurable, repeatable and presentation-ready.
**Architecture:** Extend evaluation tooling and local demo scripts around existing
providers, workflows and APIs. Preserve all frozen product contracts and runtime boundaries.
**Tech stack:** Existing Python/TypeScript, Temporal/PostgreSQL, standard-library
metrics and local Docker Compose; no mandatory model or plotting dependencies.
**Spec:** The user's Phase A / Agent 6 instructions in this conversation are binding.

## Global constraints and review focus

Offline CPU execution, public-safe original data, no model downloads in ordinary CI,
no product expansion, main/tag remain frozen. Gold annotations must not be generated
from predictions. Failed/unavailable tasks must not be removed from denominators.
Reset must only remove the dedicated local demo project's state. Controlled tampering
must always restore bytes/rows. Evidence must exclude tokens, private keys and personal paths.

## Tasks

- [x] Task 1: Add annotated synthetic assessment set and separate span/typed NER,
  classification/confusion, resolution, event extraction and retrieval metrics.
  Write meaningful metric/error tests first; run offline and probe optional profiles
  without downloading. Record versions, actual timings and resource limits.
- [x] Task 2: Add isolated start/reset/seed/demo commands, image fixture and automated
  security/reliability/performance evidence using real APIs, Temporal histories,
  object storage and crypto. Test retry-after-commit plus interrupted-worker recovery,
  and ensure counts/lineage remain stable. Run from fresh demo volumes.
- [x] Task 3: Produce concise threat/crypto/provenance/API/observability/demo documentation,
  diagrams, screenshots, academic mapping and presentation outline. Polish README;
  record actual measurements and unsupported claims. No PowerPoint or deployment.
- [x] Task 4: Run complete practical validation, audits and drift checks; independent
  branch review; fix material findings; commit clean Phase 6 branch. Do not merge/tag.

## Ledger

- Phase A initial SHA: `6ce5d40eed064664a36d300e8ec6d76d42876f5a`.
- Initial hosted run `37105843252` failed Redis container creation due to single-quote
  parsing; only health-command quoting was fixed in `be91d65`. 34 local security tests passed.
- Integration CI `37105978268` and main CI `37106125234` completed successfully
  (backend/frontend/migrations/security; manual-only local-mvp skipped as intended).
- Main fast-forwarded to `be91d6597fc14b379f57ea2c4afc099fd0a500a4`.
- Annotated tag object `8ae5ad48925a272923c9c38c4ce4579882686d91`,
  `v0.1.0-mvp`, confirmed remotely at `2026-10-03T12:54:57+05:30`.
- Phase B started from that tag in `.worktrees/evaluation-demo-hardening` on
  `phase6/evaluation-demo-hardening`. Frozen dependencies installed without changes.
- Pre-flight: assessment consumes existing immutable provider results; demo consumes
  existing source/ingestion/intelligence/security APIs; documentation consumes only
  measured assessment/demo outputs. No conflicting contract changes are required.
- Ruling: annotations are manually authored and inspected by the agent; independent
  human adjudication is pending and will be stated explicitly. Cost if wrong:
  annotation bias may distort tiny-set scores; no real-news quality claim is justified.
- Ruling: use a dedicated `aegis-demo` project with its own ports and volumes for reset
  and clean-start validation. Cost if wrong: another project's data could be lost;
  enforce a fixed project name and local Docker context before destructive reset.
- Task 1 complete: four metric/dataset tests failed on the missing assessment module
  before implementation, then passed; Ruff and strict mypy passed. Offline assessment
  ran three rounds; light/full one-round local-only probes returned ModelUnavailable.
  Whole-profile quality claims are explicitly disabled for partial probes. Raw reports
  include versions, configuration hashes, confusion matrices and timing/resource limits.
- Task 2 complete: local-context reset guards failed on missing implementation then
  four tests passed. Real post-commit Temporal retry/worker restart passed with one
  document and six analyses. Fresh reset/seed, 14 security controls (including timed
  restoration), recovery and all 22 original acceptance checks passed. Exact worker
  trace IDs were matched between Loki and collector after asynchronous-export polling.
- Ruling: collector receipt must be eventually checked and matched to a worker trace,
  not inferred from an immediate small log tail. Initial evidence check failed before
  that fix; final live evidence passed. Cost if wrong: missing telemetry could be
  mistaken for a successful observability demo.
- Task 3 complete: README, explicit future diagrams, threat/crypto/API/evaluation/demo
  docs, rubric and presentation outline written; ten optimized real screenshots captured.
  Grafana screenshot initially raced login completion; awaiting navigation fixed it.
- Validation so far: 241 backend tests with every live switch enabled, no skips;
  12 frontend tests; frontend lint/types/build/drift; Ruff and strict mypy (97 sources);
  migration roundtrip, production dependency audits and secret guard passed.
- Ruling: push only this Phase 6 branch to verify Linux hosted CI and manual clean-start
  Docker acceptance. This is within the user's remote-validation exception; main/tag
  remain frozen. Cost if wrong: public evidence or platform defects might ship unchecked.
- Final independent review: three Important findings, no Critical findings. One fix pass:
  reset pins Compose and checks resolved volume ownership; assessment breaks exact ties
  by stable document ID; invalid inference marks reports failed and CLI exits nonzero.
  Five regression tests observed RED then GREEN, 13 focused tests passed. A separate
  offline rerun reproduced all metrics and nearest-neighbor rankings exactly; reports
  were regenerated and retrieval MRR synchronized to 0.19865603146853147.
- Final: minor (deferred): nearest-rank p95 boundary is off by one when 0.95*n is integral;
  recorded n=5/16/48 measurements are unaffected. Correct before larger benchmarking.
- Final: Ruling: human adjudication remains pending under the annotation ruling above;
  no broader accuracy claim is made. Cost if wrong: labels may bias small-set scores.
- Final: Ruling: optional pretrained quality/resources stay unmeasured because models
  are unavailable. Cost if wrong: baseline scores may be mistaken for model quality;
  profile reports explicitly disable whole-profile claims.
- Final: Ruling: production identity/TLS/HA, durable trace storage, external trust anchors,
  inline media preview and downstream consumers remain deferred. Cost if wrong:
  local demonstration may be mistaken for production assurance; docs mark limitations.
- Final: Ruling: uncatchable termination cleanup is covered by isolated reset recovery,
  not a guarantee of finally execution. Cost if wrong: demo state can remain tampered
  until reset; normal caught failures restore and verify state.
- Final: Ruling: existing registry/link history and product similarity behavior remain
  frozen; assessment ties alone are corrected. Cost if wrong: product history/query
  limitations persist, but evaluation must not misstate repeatability.
- Hosted Phase 6 run 37110008028 passed all five jobs, including optional clean Linux
  Docker acceptance. Push run 37109987974 was canceled by same-ref concurrency when
  dispatch started; it was not a test failure. Final fixes will receive another full run.
- Final: fixed all three Important findings in the single pass: five regressions
  RED→GREEN; full live backend suite 246/246, no skips; format/lint/mypy/drift/secret
  guard passed. Fresh reset ignored inherited unrelated COMPOSE_FILE and passed seed,
  14 security controls, 22 acceptance controls and correlated telemetry afterward.
  Final mock suite 10/10 and live/evidence 2/2 passed; final production build passed.
- Task 4 complete: hosted run 37110699103 passed all five jobs at tested fix commit
  b28d0b1562c3a455874c1521542d10eab7c437bb. Branch-history gitleaks scanned five commits
  without leaks; committed files max 243 KB, ten screenshots total 1.06 MB; no personal
  paths found in public docs/data/config. Main and tag checked remotely and unchanged.
  Final live recovery/replay invariants passed. Slow post-restart scheduling latency
  (56.103 s median) is retained as a separate report; earlier 1.978 s batch is not
  misrepresented as a bound. Final branch is preserved, with no merge or new release.
