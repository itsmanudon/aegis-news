# Entities boundary

Canonical records remain in `aegis/domain`; model inference is in `aegis/intelligence`.

`materialize_mentions(document, analysis)` accepts a matching entity-extraction AnalysisResult,
checks its spans against the document text and creates immutable model-output EntityMention
records preserving `analysis_id`. It never writes records or upgrades evidence into facts.
Mention IDs are stable per analysis/output index, allowing an integrated service to deduplicate.

Use `Resolver.resolve(document, mentions, candidates)` for candidate-bounded resolution.
Configured aliases/exact identifiers and normalized/fuzzy names can resolve a mention; low
scores and near-ties explicitly produce `entity_id=None`. `Resolver.rank` exposes candidate
ranking for review and evaluation. No global entity graph or price data is required.
