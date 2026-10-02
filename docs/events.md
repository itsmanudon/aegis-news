# Asynchronous events and outbox

Canonical `NewsEvent` means a news occurrence/evidence record. An asynchronous envelope is a transport message with a `msg_` ID. Each concrete v1 envelope has a typed payload and rejects unknown fields. All seven exported schemas are validated by contract tests.

```json
{
  "schema_version": "1",
  "event_id": "msg_00000000-0000-4000-8000-000000000001",
  "event_type": "document.normalized.v1",
  "event_version": "1",
  "occurred_at": "2026-01-01T00:00:00Z",
  "producer": "aegis.normalization",
  "correlation_id": "example",
  "idempotency_key": "document-revision-1",
  "data": {"schema_version": "1", "document_id": "doc_00000000-0000-4000-8000-000000000002", "revision": 1}
}
```

| Event | Payload |
| --- | --- |
| document.ingested.v1 | document_id, ingestion_id |
| document.normalized.v1 | document_id, revision |
| analysis.completed.v1 | analysis_id, document_id, available_at |
| entity.resolved.v1 | entity_id, mention_id, analysis_id |
| news.event.created.v1 | event_id, revision, available_at |
| news.event.updated.v1 | event_id, revision, available_at |
| integrity.failed.v1 | subject_id, reason_code (sanitized code, not secret/raw content) |

`EventPublisher.publish()` is async. The supplied `LocalEventPublisher` is an explicit no-op, not durable delivery. No application path claims to publish news events yet. A future Kafka adapter can implement the same protocol without changing domain contracts.

`stage_event(session, envelope)` adds an outbox row to the caller's transaction and never commits or publishes. Domain write → outbox write → commit. Outbox `dispatched_at` records transport acknowledgement and is deliberately distinct from a source's `published_at`. A future dispatcher selects pending rows using `FOR UPDATE SKIP LOCKED`, publishes then records acknowledgement/attempt state, with bounded retries and recovery. Uniqueness over producer + event type + idempotency key rejects duplicate staging. Event ID is the message primary key. Derive stable idempotency keys from the business operation, not each retry's clock.

A crash after publish and before acknowledgement causes duplicate delivery. Consumers must deduplicate and process idempotently; this is at-least-once, not exactly-once. Ordering and poison-message/dead-letter policy must be designed with the first real event producer. There is no dispatcher, Kafka service, automatic retries or delivery guarantee in this phase.

## Future workflow (documented only)

NewsIngestionWorkflow: Fetch → Validate → Hash → Store → Normalize → Analyze → Resolve Entities → Extract Events → Record Provenance → Publish Intelligence. External calls belong in retryable Temporal activities; deterministic workflows orchestrate them. Domain and outbox writes share a DB transaction; object writes require compensating cleanup. Analysis availability is recorded when downstream publication becomes possible, not backdated to source publication.

The only implemented workflow is `FoundationWorkflow` → `foundation_echo`, triggered by the smoke script or integration test. It proves client → Temporal → worker activity → completed result. It has no real news behavior.
