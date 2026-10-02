# Architecture

AegisNews is an independent modular monolith with separately running background workers. `aegis/domain` owns canonical records; `aegis/contracts` owns transport schemas. Neither domain code nor contracts depend on application entrypoints or adapters. Domain feature modules depend inward on these cores. `apps/api` and `apps/worker` compose adapters. The TypeScript shell consumes only API contracts.

| Boundary | Responsibility |
| --- | --- |
| ingestion | Observe and persist raw material; future implementation |
| media | Typed S3-compatible storage port and adapter; future multimodal processing |
| normalization | Future canonical document construction |
| intelligence | Typed model ports only |
| entities | Canonical identities and external asset mappings |
| events | Versioned message contracts, publisher port and outbox staging |
| provenance | Canonical evidence-chain record, no pipeline yet |
| security | Crypto port only; future authentication and authorization |
| observability | Request context, safe JSON logging, metrics and optional traces |
| persistence | SQLAlchemy rows and transaction infrastructure |

PostgreSQL is authoritative for relationships, timestamps, analysis metadata, and outbox state. Object storage holds content bytes referenced by hashes and object locations; it is outside the PostgreSQL transaction. The ingestion phase must design orphan-object cleanup and recovery. Redis is ephemeral and never authoritative. Search starts with PostgreSQL FTS and the provisioned `pg_trgm`/`vector` extensions; no speculative vector dimensions or search indexes are created.

A module can later become a service if a real scaling or ownership requirement warrants it. Do not introduce cross-service transactions now. Consumers may interpret entity/asset identifiers using their own financial semantics; AegisNews owns no prices, portfolios, PnL, signals or backtests.

The runtime demonstrates request → bounded request/correlation IDs → FastAPI → structured JSON log and optional OTel trace context. Metrics label route templates rather than unbounded URL paths. Full Compose uses Alloy to read only the application log volume into Loki, with no Docker socket access. Grafana provisions Prometheus and Loki; traces are exported to the collector's debug sink without a trace database. Worker log/trace propagation and production observability are future work.

[Decisions](adr/README.md) explain the retained boundaries and local infrastructure choices.
