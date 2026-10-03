# Assessment and performance methodology

16 original CC0 English texts, 17 mentions, 13 event sentences, eight categories and
16 coarse retrieval-partner judgments. Labels were authored before inference. Offsets,
IDs and relevance references validate. [Annotation policy](../../ml/datasets/gold/README.md).
**Human adjudication is pending**; no inter-annotator agreement, held-out real-news test,
training, fine-tuning or statistical quality claim is made.

## Task protocols and measured offline scores

NER matches exact document/start/end; typed scores additionally require semantic kind.
The capitalized-span baseline emits `other`, so typed F1 is zero. IBM is a deliberate
single-token miss. Classification macro F1 averages over observed gold/predicted labels,
including unavailable outcomes; confusion matrices expose taxonomy/lexicon weaknesses.
Resolution uses gold mentions and tiny supplied candidate sets independently of NER,
including two correct unresolved cases. Top-3 includes correct abstentions and primarily
measures candidate coverage/safety, not large-scale entity linking.

Event extraction set scores match document, type and exact trimmed sentence evidence.
Classification separately predicts an annotated summary, retaining event ID/revision.
Thirteen gold sentences produce ten matches; three paraphrases are missed. No extraction
on three general items is a correct empty prediction. Retrieval excludes self and ranks
compatible vectors; one manually chosen category partner per query is a coarse, incomplete
relevance judgment. Exact score ties use stable document IDs within assessment tooling;
random analysis IDs cannot change the measured ranking. Nearest-neighbor examples are
in the raw report, indexed by stable IDs.

| Offline task | Precision | Recall | F1 / macro F1 | Accuracy |
|---|---:|---:|---:|---:|
| NER span-only | 1.000 | 0.941 | 0.970 | — |
| NER typed | 0.000 | 0.000 | 0.000 | — |
| Topics | — | — | 0.567 | 0.750 |
| Sentiment | — | — | 0.390 | 0.500 |
| Event extraction | 1.000 | 0.769 | 0.870 | — |
| Event classification | — | — | 0.810 | 0.813 |
| Candidate resolution | — | — | — | 1.000 |

Retrieval MRR 0.1987, recall@3 0.1875. Hash collisions/shared words often outrank the
category partner; this is lexical hashing, not learned semantics. [Offline raw report](../../ml/evaluation/results/offline.json).

## Profiles, versions and resources

Offline `capitalized-spans`, `keyword-topics`, `lexicon-sentiment`, `hash-vectors`,
`keyword-events`, `candidate-resolver`: baseline revision 1. Raw reports preserve package/
implementation versions, registry/configuration hashes, device and dimensions.
Three rounds cover 48 document passes, including cold/warm overhead and `tracemalloc`.
Python allocation peak is about 0.5 MB; native allocations, process RSS and Docker memory
are excluded. Provider medians are approximately 0.5–2.2 ms on the recorded Windows CPU
environment. No GPU or downloads. Short texts and tracing overhead prevent extrapolation.
Valid empty `NoPredictions` outcomes retain their denominators. Unexpected inference
errors invalidate whole-profile claims and cause a nonzero CLI exit after writing
diagnostics; unavailable optional models remain an explicitly partial local-only probe.

Docker reported 32 logical CPUs and 15.47 GiB available memory. A post-demo snapshot
showed API 141.6 MiB and worker 135.4 MiB; these are idle/current container measurements,
not peaks or isolated model-memory measurements. Other local projects/builds shared
the host. A later fresh run measured total median 2.461 s (p95 2.527 s), illustrating
runtime variability; the published stage table below is the first recorded batch.

Light uses pinned bert-base-NER, finbert and all-MiniLM-L6-v2 plus keyword topic/events.
Full adds bart-large-mnli and all-mpnet-base-v2. Exact model/revision/configurations appear
in [light](../../ml/evaluation/results/light-probe.json) and [full](../../ml/evaluation/results/full-probe.json)
reports. Local-only probes found `ModelUnavailable`: optional packages/artifacts are not
installed. Pretrained quality, throughput, RAM/VRAM and download sizes are **not measured**.
Zero bytes were downloaded. Partial baseline successes/abstentions are retained for
diagnosis, with whole-profile quality flag false; they are not pretrained quality results.

```sh
uv sync --frozen
uv run python scripts/build_assessment_set.py
uv run python -m aegis.intelligence.assessment --profile offline --rounds 3 --output ml/evaluation/results/offline.json
uv run python -m aegis.intelligence.assessment --profile light --rounds 1 --output ml/evaluation/results/light-probe.json
uv run python -m aegis.intelligence.assessment --profile full --rounds 1 --output ml/evaluation/results/full-probe.json
```

Optional model installation/download is a separate explicit step; see Agent 2's
`ml/models/requirements-local.txt` and model documentation. Ordinary CI never performs it.

## Real local pipeline performance

Five concurrent short synthetic items on fresh isolated demo volumes, offline profile.
Temporal server activity-start/completion timestamps include model, SQL and object I/O.
Total workflow includes scheduling gaps; adding stage medians is not the total median.

| Stage | Median ms | p95 ms |
|---|---:|---:|
| Acquire/validate/hash/store/persist | 62.970 | 74.394 |
| Normalize | 39.361 | 52.342 |
| Commit document/media/outbox | 30.054 | 45.074 |
| Entities | 37.502 | 54.085 |
| Topics | 47.217 | 51.710 |
| Sentiment | 38.929 | 59.033 |
| Embedding | 39.864 | 60.274 |
| Resolution | 63.212 | 82.074 |
| Events | 52.954 | 79.850 |
| Provenance/sign/encrypt/store | 101.473 | 130.252 |
| Total workflow | 1978.154 | 2001.632 |

Batch wall including polling/verification 2.878 s; throughput 1.737 docs/s.
With n=5, nearest-rank p95 is the maximum, not a stable population percentile. Host
workload/container scheduling were uncontrolled. [Raw measurement](../evidence/pipeline-benchmark.json).
Repeated benchmark keys reuse the original workflows; the updated runner reports no
fresh throughput for cached replay. Reset before comparing fresh processing runs.
