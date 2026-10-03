# Original synthetic assessment set

Reviewed version: [gold v2](assessment-v2.json), [review record](ADJUDICATION-v2.md),
[field-level decisions](adjudication-v2.json), [integrity manifest](manifest-v2.json).
The review is a single agent pass, **not independent human adjudication**. Two label
decisions changed; all 16 texts and 17 spans are preserved, with 12 typed event
sentences after removing the museum/company-launch mismatch. Human sign-off is pending.
Both profiles were rerun using this exact set; [results and limitations](../../../docs/evaluation/light-vs-offline.md).
The sections below describe the unchanged provisional v1, not a completed human review.

`assessment-v1.json` contains 16 original short English items in eight categories:
business, economics, technology, public policy, regional, commodities, cyber/security,
and media. Texts and the schematic PNG in `data/samples/demo-image.png` are CC0-1.0.
Names and events are fictional; IBM is merely an entity-label example, not a factual claim.
No article dumps, copyrighted imagery or personal data are included.

Annotations were authored and manually inspected by the agent before inference.
**Independent human adjudication is pending.** Reviewers should inspect and revise the
labels before treating this as an academic gold standard. It is a development set,
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
