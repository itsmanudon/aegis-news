# ADR-001: Modular monolith plus background workers

Status: Accepted for foundation

## Context

An early independent platform needs explicit module ownership without distributed transaction and deployment overhead.

## Decision

Use Python modules in one application package, composed by FastAPI and Temporal workers. Domain and transport contracts form the inward dependency boundary.

## Consequences

Modules can be extracted later when measured workloads or ownership justify it. Shared database ownership requires discipline; no microservice deployment is introduced.
