# Local intelligence model registry

`aegis.intelligence.config` owns immutable model specifications. Providers implement the
unchanged ports in `aegis/intelligence/interfaces.py`. No paid API, external MLflow server,
GPU, network access or model installation is required for the offline profile or normal CI.
Real inference uses task-specific local models, never a combined LLM pipeline.

| Task | Light | Full | Approximate FP32 weights |
| --- | --- | --- | --- |
| NER | dslim/bert-base-NER | same | 430 MB |
| Document/context sentiment | ProsusAI/finbert | same | 440 MB |
| Topics | keyword baseline | facebook/bart-large-mnli | rules / 1.6 GB |
| Embeddings | all-MiniLM-L6-v2, 384 dimensions | all-mpnet-base-v2, 768 dimensions | 90 MB / 440 MB |
| Event extraction/classification | sentence keyword baseline | BART MNLI, shared with topics | rules / shared |
| Entity resolution | aliases, normalized names, exact identifiers, fuzzy candidate ranking | same | no weights |

Model cards: [NER](https://huggingface.co/dslim/bert-base-NER),
[FinBERT](https://huggingface.co/ProsusAI/finbert),
[MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
[MPNet](https://huggingface.co/sentence-transformers/all-mpnet-base-v2),
[BART MNLI](https://huggingface.co/facebook/bart-large-mnli).
Sizes are rough weight estimates, not measured runtime benchmarks. Allow approximately
4–6 GB free RAM for light and 8–12 GB for full, plus Python/PyTorch installation space.
Light works on CPU; full works on CPU but zero-shot classification is slow. GPU use is optional
and configurable via `ModelSpec.device`; actual memory/latency depends on hardware and text size.
Weights are lazy-loaded and cached; zero-shot tasks share one model, and a runtime serializes
model inference. Production workers should limit concurrent AI activities on each machine.

The explicit `offline` profile uses capitalization NER, keyword topics/events, lexicon sentiment
and 64-dimensional token hash vectors. Hash vectors are **not semantic embeddings**. This profile
is a deterministic wiring baseline, not a substitute for real NER or sentence-transformer models.

## Setup and reproducibility

Use a separate inference environment if you want to keep the normal CI environment small:

```sh
pip install -e .
pip install -r ml/models/requirements-local.txt
# Export metadata only; does not download anything.
python -m aegis.intelligence.models --profile light --manifest model-manifest.json
# Explicit network/download step, outside normal CI.
python -m aegis.intelligence.models --profile light --download --manifest model-manifest.json
python -m aegis.intelligence.evaluation --profile light --output evaluation.json
```

The download command pins immutable upstream commit SHAs, prefers safetensors when supplied
by the upstream repository, fetches only the required PyTorch/tokenizer/configuration files,
and records their SHA256 checksums. FinBERT's pinned repository uses PyTorch weights; the optional
environment requires torch >=2.6. Model weights and generated manifests are not committed.
Keep the manifest and evaluation report together for each experiment, plus an exact package lock
and the AegisNews Git SHA. No MLflow dependency was added.

Inference defaults to `local_files_only=True` and never implicitly falls back to a different
model or a paid service. Missing packages/weights raise `ModelUnavailable`. Custom models are
configured with a `Profile` JSON or Python object; HF revisions must be 40-character commit SHAs.
Custom classifiers must expose meaningful sentiment labels or the documented taxonomy labels.

```python
from pathlib import Path
from aegis.intelligence.config import Profile
from aegis.intelligence.engine import build_engine

specs = Profile.model_validate_json(Path("profile.json").read_text())
ai = build_engine(specs)  # or build_engine("light"), build_engine("full")
analysis = await ai.embeddings.embed(document)
```

Every output is wrapped in immutable `AnalysisResult`: a new `analysis_id`, provider, model name,
pinned version, effective configuration hash, inference start `created_at` and completion
`available_at`. The hash includes implementation version, model settings, taxonomies, lexicons,
runtime library versions and task context. No timestamp is copied from article publication time.
Store the exact input NewsDocument revision with your run manifest: frozen v1 AnalysisResult has
no document-revision field, and this implementation does not redesign that contract.

Token-aware chunking covers document text instead of silently taking a prefix. Document embeddings
are normalized token-weighted means of chunk embeddings, suitable for pgvector numeric arrays.
NER offsets are always Python character offsets in `NewsDocument.text`; title is not prepended.
Classification/sentiment use document text too. Boundary-spanning NER entities can be split.

## Limitations

The initial downloadable profiles support English only; other declared languages fail explicitly.
Absent language means English is assumed. Topic/event rules are uncalibrated, simple keyword
baselines. Zero-shot event labels are proposals, not assertions that an event occurred. Dates are
left unresolved (`occurred_at=None`). FinBERT is financial-domain sentiment and may be less useful
on general/regional news. Entity-targeted sentiment is a sentence-context proxy and can confuse
multiple entities in the same sentence; it is not a trained aspect sentiment model. Sentiment
never represents expected returns, investment recommendations or trading signals.

The resolver operates only over supplied candidates. It does not perform global candidate
retrieval, price lookup or stock mapping. Embedding-based resolution is not implemented in this
baseline. Rule confidence values and fuzzy scores should not be treated as calibrated probabilities.

Frozen AnalysisResult requires nonempty outputs. Empty NER/event/resolution findings raise
`NoPredictions`; no placeholder entity/event or empty analysis is invented. Malformed model
predictions raise `InvalidPrediction`; inference errors create no analysis. The future workflow
should handle no-findings separately from retryable model/service failures.

## Integration

`apps.worker.ai_activities.AIActivities(build_engine(profile)).registered()` returns seven bound
activities: analyze_entities, analyze_topics, analyze_sentiment, generate_embedding,
resolve_entities, extract_events and classify_event. Single-document tasks accept canonical
NewsDocument; multi-input tasks accept frozen `ResolutionRequest`, `EventRequest` or
`EventClassificationRequest`. Document-ID loading belongs to the integrated workflow/repository.

Configure the Temporal client with the SDK's
[Pydantic v2 data converter](https://python.temporal.io/temporalio.contrib.pydantic.html)
(`temporalio.contrib.pydantic.pydantic_data_converter`), then register the bound activities on
the worker. The existing foundation worker/workflow is intentionally unchanged. Set suitable
activity timeouts and concurrency for local CPU inference; no model runs inside workflow code.
Treat `NoPredictions` and `UnsupportedLanguage` as non-retryable task outcomes. Direct library
calls expose those typed exceptions; the activities translate them into non-retryable Temporal errors.

`aegis.entities.materialize.materialize_mentions(document, extraction_analysis)` explicitly
creates only `evidence_kind="model_output"` mentions, with the extraction `analysis_id`.
Mention IDs are deterministic for an analysis and output index. Resolver outputs are new analyses;
the caller decides how to link them to mentions. No canonical events or fact mentions are created.

`aegis.intelligence.persistence.append_analysis(session, analysis)` appends an ORM row using the
existing analyses table; the caller owns document foreign keys, transactions, retry deduplication
and outbox publication. It never merges/updates an existing analysis. Existing DB triggers enforce
immutability. **No migration was added**; no `ai_0001` is necessary. Numeric vectors remain in
EmbeddingResult/analyses JSONB. The CPU similarity helper compares compatible spaces only and
filters by `available_at <= as_of`; no external vector store or pgvector index is introduced.

Repeated activity attempts generate new analysis IDs. Persist once per accepted task result and
deduplicate at the orchestration layer; timestamps are actual attempt times. No claiming production
model accuracy is justified by the synthetic fixture evaluation. Pretrained weights were not
downloaded or benchmarked during CI validation.
