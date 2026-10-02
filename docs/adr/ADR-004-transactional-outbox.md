# ADR-004: Transactional outbox with optional Kafka

Status: Accepted for foundation

## Context

Persisting data then directly publishing can lose messages or expose uncommitted records. Kafka must not be required for the MVP.

## Decision

Stage validated versioned envelopes in outbox_events on the caller transaction. Define an EventPublisher protocol and an explicitly no-op local publisher.

## Consequences

Future dispatch is at least once with deduplication, retry and acknowledgement state. A committed row does not yet imply delivered event; no dispatcher or Kafka deployment exists.
