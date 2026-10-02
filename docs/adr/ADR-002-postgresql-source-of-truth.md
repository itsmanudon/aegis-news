# ADR-002: PostgreSQL as application source of truth

Status: Accepted for foundation

## Context

Relationships, immutable analyses, precise times and atomic event staging need transactional persistence.

## Decision

Use PostgreSQL with SQLAlchemy and Alembic. Persist metadata and outbox in the same transaction; use JSONB only for uncertain typed model outputs/evidence structures.

## Consequences

Object bytes remain in S3 and Redis is ephemeral. Initial extensions are vector and pg_trgm; feature-specific indexes/dimensions wait for query evidence.
