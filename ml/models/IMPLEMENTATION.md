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
