# Canonical domain v1

Pydantic records reject unknown fields and are frozen. Nested analysis outputs use frozen records and tuples. All timestamps must be timezone-aware and persist as PostgreSQL `timestamptz`; UTC is recommended on the wire. `schema_version = "1"` is serialized. Schema-breaking changes require a new version and an explicit migration/compatibility decision.

IDs are opaque prefixed UUIDs. `new_id()` centrally generates UUID4 for Python 3.12 portability. UUIDv7 may replace generation later without changing wire shape; consumers must never infer time/order from IDs. Contracts enforce the appropriate prefix and UUID shape.

| Record | Identifier | Role |
| --- | --- | --- |
| Source | src_ | Publisher/provider metadata |
| RawIngestion | ing_ | Raw observation, source reference and object/hash pointer |
| MediaAsset | media_ | Ingestion-owned content reference |
| DocumentMediaLink | document_id + media_id | Explicit canonical document/media association |
| NewsDocument | doc_ | Canonical text and its original temporal lineage |
| Entity | ent_ | Organization/person/location identity |
| EntityMention | mention_ | Document text span and declared evidence kind |
| AssetMapping | map_ | External ISIN/provider ID or exchange symbol + venue |
| TopicResult | within analysis | Topic prediction + confidence |
| SentimentResult | within analysis | Model sentiment; score [-1,1], not expected return |
| EntityExtractionResult | within analysis | Predicted surface/span, optional entity kind and confidence |
| EntityResolutionResult | within analysis | Mention resolution prediction, including unresolved identity |
| EmbeddingResult | within analysis | Nonempty finite vector; dimensions equal the number of values |
| EventExtractionResult | within analysis | Proposed event type, confidence and document evidence |
| EventClassificationResult | within analysis | Label/confidence targeting an exact event_id + event_revision |
| AnalysisResult | ana_ | Immutable model metadata and typed outputs |
| NewsEvent | evt_ + revision | Fact or model-derived event with supporting documents |
| ProvenanceRecord | prov_ | Hash, operation and explicit input references |
| Async envelope | msg_ | Transport identity, distinct from canonical event identity |

## Time semantics

| Timestamp | Meaning | Future downstream use |
| --- | --- | --- |
| published_at | Publisher/source's claimed publication time, nullable | Descriptive source claim; may be wrong/future |
| first_seen_at | First observation by AegisNews | Earliest local observation |
| ingested_at | Time the ingestion was persisted | Durable raw availability |
| available_at | Time a derived result became available to downstream consumers | Knowledge cutoff for historical consumers |

Never substitute `published_at` for any of the other three. First observation must precede ingestion; document creation must not precede ingestion. Publisher time has no enforced relationship to local arrival times. `created_at` measures record/inference creation; `available_at >= created_at`. A future pipeline must record actual publication/visibility time and enforce cross-record lineage; merely having an earlier source date does not make an analysis historically available.

Downstream historical consumers select `available_at <= cutoff`, including any revision they use. A new model run receives a new analysis ID, provider/name/version/configuration SHA-256, created time and actual availability time. PostgreSQL rejects analysis UPDATE/DELETE and contracts are frozen. Old outputs survive model upgrades. Reproduction also requires retention of model artifacts, exact configuration, inputs, execution dependencies and seeds where applicable; the foundation stores metadata and does not implement that artifact pipeline.

Entity mentions distinguish facts from model outputs; model mentions need an analysis reference. News events do the same, with optional occurrence time; event classification is a typed model output. Unresolved entity resolution is explicit (`entity_id = null`). Facts do not acquire fabricated confidence/model metadata.

## Model output lifecycle

All six intelligence protocols return immutable `AnalysisResult`: model output → `AnalysisResult` → a future domain service may derive canonical records. The analysis owns `analysis_id`, document context, provider, model name/version, configuration hash, creation time and actual `available_at`. Its nonempty typed outputs must match `analysis_type`: topic, sentiment, entity extraction, entity resolution, embedding, event extraction or event classification. Nested outputs are predictions, not independently persisted canonical facts; preserve their enclosing analysis when passing them between boundaries.

`EntityExtractor` returns `EntityExtractionResult` predictions inside analysis, never canonical mentions. Offsets are a nonempty half-open span in the analyzed document text. A later service may create `EntityMention(evidence_kind="model_output", analysis_id=...)`; fact mentions must have no analysis ID. `EmbeddingProvider` returns an embedding analysis with finite vector values, using the same lineage as every other inference. No vector index or model inference is implemented.

`EventExtractor` returns proposed event types and evidence text tied to the analyzed document, with an optional source occurrence time. Occurrence time does not determine intelligence availability. A later service may derive `NewsEvent(evidence_kind="model_output", analysis_id=...)`; extraction itself allocates no canonical event identity. `EventClassificationResult` requires both `event_id` and `event_revision >= 1`, with no default revision or implicit latest-state lookup. Historical consumers can identify the exact classified event state. Cross-record existence and evidence validation belongs to future domain services; event references within analysis JSON are not SQL foreign keys.

The classification revision is an intentional correction to the pre-product domain v1 contract: old classification payloads without a revision now fail validation. No revision is inferred or backfilled into immutable historical analysis. No async v1 envelope changes are required.

## Document/media association

`DocumentMediaLink(document_id, media_id)` is backed by `document_media`, with a composite primary key and foreign keys to documents and media assets. A document can link multiple media assets, and a media asset can be shared by multiple documents. Duplicate links and missing endpoints are rejected. The ingestion reference still records a media asset's origin; matching ingestion IDs never establishes an association. One ingestion may create several documents, and explicit links may cross ingestion origins. No automatic backfill can safely infer those links.

The link carries only endpoint IDs and schema version; roles/order wait for concrete requirements. Endpoint deletion requires explicitly removing links first (no cascade). The primary key supports document lookup, and a media ID index supports reverse lookup.

An entity such as Apple Inc. can map to `NASDAQ` + `AAPL` and an ISIN; an Indian entity can map to NSE/BSE identifiers and ISIN. No price, portfolio, PnL, buy/sell or expected-return field belongs here.

## Persistence scope

The initial schema contains sources, raw objects, ingestions, documents, media assets, entities, mentions, asset mappings, analyses, revisioned events and event joins, provenance records, and outbox events. Forward migration `0002_contract_hardening` adds `document_media` without rewriting `0001_foundation`. All seven output types remain typed JSON in immutable analyses until query requirements justify projections. Users/roles/permissions/audit/signatures/entity aliases are deferred.

Foreign keys preserve relationships, uniqueness constrains ingestion/outbox retries, and database checks preserve time ordering and evidence references. Application domain validation remains required before persistence; SQLAlchemy is not a substitute for canonical validation. Direct SQL type/enumeration parity and a restricted database application role are future hardening tasks.
