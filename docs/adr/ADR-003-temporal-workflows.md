# ADR-003: Temporal for background orchestration

Status: Accepted for foundation

## Context

Future ingestion needs retryable activities and durable workflow history.

## Decision

Provide a Temporal development server and one no-side-effect workflow/activity. Use a test trigger rather than exposing a product workflow route.

## Consequences

Local orchestration history uses a dedicated SQLite volume for the CLI development server; application source of truth stays PostgreSQL. Hardened self-hosting and actual news workflows are deferred.
