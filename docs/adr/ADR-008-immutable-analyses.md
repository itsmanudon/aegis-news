# ADR-008: Immutable versioned analysis results

Status: Accepted for foundation

## Context

Model upgrades must not overwrite historical knowledge or introduce look-ahead bias.

## Decision

Create a new ana_ record for each analysis with provider/name/version/config hash, created_at and available_at. Freeze Pydantic outputs and reject UPDATE/DELETE in PostgreSQL via a trigger.

## Consequences

Metadata supports artifact reproducibility but does not itself retain executable model/config artifacts. New runs remain independently queryable. Privileged maintenance/deletion policy requires a future explicit security decision.
