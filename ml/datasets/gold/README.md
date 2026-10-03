# Gold evaluation dataset history

| Version | Review status | Files |
|---|---|---|
| Gold v1 | Original agent-authored provisional set | [assessment-v1.json](assessment-v1.json) |
| Gold v2 | One agent adjudication pass; never human-reviewed | [assessment-v2.json](assessment-v2.json), [decisions](adjudication-v2.json), [rationale](ADJUDICATION-v2.md), [manifest](manifest-v2.json) |
| Gold v3 | Independent review completed by one human | [assessment-v3-human.json](assessment-v3-human.json), [manifest](manifest-v3-human.json) |

Gold v3 is the current reviewed evaluation reference: all 16 cases have `status: reviewed`.
The human accepted every v2 label: zero changed cases/fields. It preserves all documents,
17 entity spans/types/resolution targets, 12 typed event sentences, retrieval partners
and two image references. Original versions and historical results remain unchanged.

Each case's `adjudication.original_labels` snapshots v2 topic, sentiment, event and entities
(including offsets and resolution IDs). `pending_review` means not checked by the human;
`reviewed` means checked. Empty `changes` means acceptance; nonempty changes require
`field`, `old_value`, `new_value`, with `reason` when supplied, and matching current values.
`notes` is the reviewer's text. No agent opinions were added to these review blocks.
Inherited `annotation_note` remains historical agent-authored context, not the human's rationale.

`python -m scripts.validate_gold_v3` checks review completion, original document/label
snapshots, exact offsets, logged changes, unique IDs, taxonomy/reference validity and
manifest hashes. It never decides whether the human's label is semantically correct.
`--write-manifest` explicitly generates a new receipt; use it only when freezing a new
review version, not to hide tampering. Keep a frozen dataset unchanged after benchmarking.

[Gold v3 CPU/GPU evidence](../../../docs/evaluation/gold-v3-gpu.md) reports fresh runs with
unchanged metrics/models. One reviewer, short synthetic CC0 English items, organization-heavy
NER, incomplete retrieval judgments and tiny candidates do not establish general news quality.

The sections below document the original provisional v1 methodology.


`assessment-v1.json` contains 16 original short English items in eight categories:
business, economics, technology, public policy, regional, commodities, cyber/security,
and media. Texts and the schematic PNG in `data/samples/demo-image.png` are CC0-1.0.
Names and events are fictional; IBM is merely an entity-label example, not a factual claim.
No article dumps, copyrighted imagery or personal data are included.

Annotations were authored and manually inspected by the agent before inference.
At v1 publication, independent human adjudication was pending; v3 records the later review.
This remains a development-derived small set,
not a held-out real-news test set. Do not tune the baseline to improve these scores.

Each case includes human-readable text, primary topic, overall sentiment, exact entity
offsets/types, candidate mappings, expected event evidence/type, and one explicitly
judged retrieval partner. Positive means beneficial reported outcome; negative means
adverse outcome; mixed combines benefit/recovery and harm; neutral describes an action
without a clear valence. Topic taxonomy overlaps, and several labels are debatable.
Metro Council deliberately has two identical candidate names and must stay unresolved.
IBM has no supplied candidate and must also remain unresolved. Entity resolution is
evaluated with gold mentions, separately from extraction errors.

Event extraction matches document ID, event type and exact trimmed sentence evidence.
Classification is evaluated separately against the annotated event summary, including
`general` for no specific event. A missing optional model remains an abstention/error
in classification denominators. Retrieval partners are coarse category relevance
judgments, not complete graded relevance or a semantic-search benchmark.

Rebuild byte-for-byte inputs with `uv run python scripts/build_assessment_set.py`.
The script contains all manually chosen texts/labels and computes offsets mechanically;
it never reads provider predictions. Original Agent 2 `synthetic.jsonl` remains unchanged.
