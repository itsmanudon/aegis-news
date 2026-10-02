# Canonical domain v1

Pydantic records reject unknown fields and are frozen. Nested analysis outputs use frozen records and tuples. All timestamps must be timezone-aware and persist as PostgreSQL `timestamptz`; UTC is recommended on the wire. `schema_version = "1"` is serialized. Schema-breaking changes require a new version and an explicit migration/compatibility decision.

IDs are opaque prefixed UUIDs. `new_id()` centrally generates UUID4 for Python 3.12 portability. UUIDv7 may replace generation later without changing wire shape; consumers must never infer time/order from IDs. Contracts enforce the appropriate prefix and UUID shape.

| Record | Identifier | Role |
| --- | --- | --- |
| Source | src_ | Publisher/provider metadata |
| RawIngestion | ing_ | Raw observation, source reference and object/hash pointer |
| MediaAsset | media_ | Ingestion-owned content reference |
| NewsDocument | doc_ | Canonical text and its original temporal lineage |
| Entity | ent_ | Organization/person/location identity |
| EntityMention | mention_ | Document text span and declared evidence kind |
| AssetMapping | map_ | External ISIN/provider ID or exchange symbol + venue |
| TopicResult | within analysis | Topic prediction + confidence |
| SentimentResult | within analysis | Model sentiment; score [-1,1], not expected return |
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

An entity such as Apple Inc. can map to `NASDAQ` + `AAPL` and an ISIN; an Indian entity can map to NSE/BSE identifiers and ISIN. No price, portfolio, PnL, buy/sell or expected-return field belongs here.

## Persistence scope

The initial schema contains sources, raw objects, ingestions, documents, media assets, entities, mentions, asset mappings, analyses, revisioned events and event joins, provenance records, and outbox events. Topic/sentiment outputs remain typed JSON in immutable analyses until query requirements justify projections. Users/roles/permissions/audit/signatures/entity aliases are deferred.

Foreign keys preserve relationships, uniqueness constrains ingestion/outbox retries, and database checks preserve time ordering and evidence references. Application domain validation remains required before persistence; SQLAlchemy is not a substitute for canonical validation. Direct SQL type/enumeration parity and a restricted database application role are future hardening tasks.
