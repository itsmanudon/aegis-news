# API v1 foundation

`GET /health` is process liveness and does not inspect dependencies. `GET /ready` checks PostgreSQL connectivity + the migrated outbox table, Redis PING, and the configured S3 bucket; it checks Temporal when enabled. All probes have timeouts. Readiness failure returns HTTP 503 in the error envelope without credentials or dependency exception text. Probe results on success list required dependencies.

`GET /api/v1/system/info` returns name, version, foundation stage and architecture. Reserved router modules: `/api/v1/documents`, `/entities`, `/events`, `/search`, `/assets`. No product handlers are registered. `/docs`, `/redoc` and `/openapi.json` expose generated documentation; `/metrics` uses Prometheus text format and is excluded from OpenAPI.

```json
{"data": {}, "meta": {"request_id": "opaque-id", "api_version": "v1"}}
```

```json
{"data": [], "pagination": {"next_cursor": null, "has_more": false}, "meta": {"request_id": "opaque-id", "api_version": "v1"}}
```

Collections use cursor pagination only. Future cursors are opaque tokens bound to stable ordering, filters and a knowledge cutoff when relevant. No pagination engine or public collection endpoint is implemented. `has_more` must agree with `next_cursor` being present.

```json
{"error": {"code": "INVALID_ARGUMENT", "message": "Request validation failed", "request_id": "opaque-id"}}
```

Codes: INVALID_ARGUMENT, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, RATE_LIMITED, SOURCE_UNAVAILABLE, PROCESSING_FAILED, INTEGRITY_FAILED, INTERNAL_ERROR. HTTP exceptions, validation errors, unmatched routes, method errors and unexpected handler failures share this structure. Preserve useful authentication/retry headers. Error text never includes raw validation input or internal exception details. The foundation adds error codes, not authentication or rate limiting.

Clients may send `X-Request-ID` and `X-Correlation-ID` (1–128 ASCII letters/digits/period/underscore/hyphen); malformed or oversized values are replaced. Responses echo valid IDs or generated UUIDs. OTel independently handles W3C `traceparent` when enabled. Correlation IDs are observational context and are never authentication/idempotency credentials.

OpenAPI and JSON schemas are checked in under `schemas/`. Run `uv run python scripts/export_schemas.py` after intentional contract changes; CI fails on drift. Generated SDKs are deferred. Interactive documentation and metrics are local development facilities; production exposure requires explicit access policy.

The implementation follows the official [Pydantic model guidance](https://docs.pydantic.dev/latest/concepts/models/) and [Next.js setup guidance](https://nextjs.org/docs/app/getting-started/installation); frontend lint is a separate CI step.
