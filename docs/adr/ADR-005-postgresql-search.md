# ADR-005: PostgreSQL search before OpenSearch

Status: Accepted for foundation

## Context

Early search requirements do not justify an additional distributed index.

## Decision

Reserve PostgreSQL FTS, pg_trgm and pgvector as the initial search options; provision extensions only.

## Consequences

No OpenSearch dependency. Vector dimensions, embedding persistence and indexes follow real models/query workloads.
