# Local intelligence design and implementation plan

Implement the supplied Agent 2 mission at base 0203ae95aa1fdf75dd05862c404b5cc743a01f55.
The domain records and existing ports are frozen. Separate providers implement each port;
a shared envelope factory handles immutable metadata, and lazy local runtimes handle weights.
No ingestion workflow, security, frontend, or canonical-event creation is included.

1. Write offline tests for envelopes, metadata, failure, spans, dimensions, swapping and revisions.
   Run them before implementation. Add immutable model specifications, profiles, taxonomies,
   envelope creation and separate task providers. Run these tests.
2. Test resolver ambiguity and alias matching, mention lineage, append-only ORM adaptation,
   and typed worker requests. Implement these adapters without schema changes.
3. Test evaluation metrics on hand-computed examples. Add synthetic gold data, raw/silver/gold
   conventions, CLI evaluation and an explicit model download command. Document resources,
   pinned revisions, known biases, and integration. Run full pytest, Ruff and mypy.
4. Review the complete diff against the mission, commit only this branch and report the SHA.

Review focus: empty predictions cannot fit the nonempty frozen envelope; malformed offsets must
fail; inference completion is the earliest available_at; wrong vector spaces must not compare;
an ambiguous alias must remain unresolved; long documents must not silently truncate; event
classification must preserve the existing revision; offline inference must not fetch weights.

No-predictions is a typed exception, not a fabricated output. Task failure creates no analysis.
Light uses NER + sentiment + MiniLM on CPU, with explicit rules for topics and events. Full adds
BART MNLI and MPNet. Offline uses deterministic baselines (including nonsemantic hash vectors)
and is for wiring/evaluation smoke tests only. Runtime metadata includes pinned model identity,
configuration, taxonomy, implementation and library versions. Persistence reuses analyses JSONB.

## Completion record

Implemented all four steps in the isolated feat/ai-intelligence worktree. Offline tests cover
the complete pipeline, immutable envelopes, metadata/configuration hashing, provider replacement,
model loader arguments, token windows, resolution, revisions, persistence, payload conversion,
failure handling and independently hand-computed evaluation metrics.

Independent review identified invalid upper-bound span acceptance and zero-margin exact-tie
resolution. Both were reproduced with failing regression tests and fixed. Raw local NER offsets
also reject lossy integer coercion and out-of-chunk bounds. Domain/contracts/interfaces remain
unchanged. The reviewer set aside ingestion registration, candidate retrieval, canonical-event
materialization, actual weight benchmarks and DB service checks as intentionally outside this
branch's scope; integration/docs explicitly describe these responsibilities and limits.

Custom ModelSpecs with different inference settings can cache separate copies of the same
weights; built-in full-profile zero-shot tasks share one model. This optimization is deferred.
No schema migration, external MLflow requirement, main edit, merge or push was made.

Full checks: Ruff formatting/lint, strict mypy, pytest, schema export, offline evaluation and
manifest export. The optional migration round-trip check could not authenticate to the local
PostgreSQL service; no migration files changed. Pretrained weights were not downloaded in tests.
