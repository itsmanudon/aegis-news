# ADR-006: S3-compatible object storage

Status: Accepted for foundation

## Context

Multimodal raw content must not couple domain behavior to one vendor.

## Decision

Depend on ObjectStorage with async put/get/delete/exists/metadata. Implement an S3 adapter and local MinIO container built from pinned upstream source because official images are unavailable.

## Consequences

Bucket initialization is local infrastructure. Object writes are not atomic with PostgreSQL; cleanup/reconciliation belongs to ingestion. Review upstream maintenance before production.
