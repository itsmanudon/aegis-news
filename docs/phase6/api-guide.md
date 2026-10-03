# API reproduction examples

API base `http://localhost:38000`, Swagger `/docs`, machine schema `/openapi.json`.
Normal product routes require a bearer token. Local health/readiness/docs/metrics are
system routes. Analyst can read/verify; admin/source-manager scopes allow ingestion;
viewer ingestion is 403. Audit requires `audit:read`. See full [method/scope inventory](../mvp-integration.md).

Generate a local token with `python scripts/demo.py token --role admin` and keep it in
`AEGIS_TOKEN` privately. The following standard-library example creates a source and
submits an original article plus PNG through the actual API. It does not print the token.
Run with the locked Python environment (`uv run python ...`).

```python
import base64
import json
import os
import urllib.request
from pathlib import Path

base = "http://127.0.0.1:38000"


def call(path, body=None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + os.environ["AEGIS_TOKEN"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


source = call("/api/v1/sources", {"name": "Original API example", "kind": "upload"})["data"]
article = {
    "title": "Atlas Labs launches a workshop",
    "text": "Atlas Labs launched software with improved reliability.",
    "language": "en",
    "published_at": "2020-01-01T00:00:00Z",
}
submission = call(
    "/api/v1/ingestions",
    {
        "source_id": source["source_id"],
        "idempotency_key": "api-example-v1",
        "content_type": "application/json",
        "content_base64": base64.b64encode(json.dumps(article).encode()).decode(),
        "correlation_id": "api-example-v1",
        "media": [
            {
                "kind": "image",
                "content_type": "image/png",
                "content_base64": base64.b64encode(
                    Path("data/samples/demo-image.png").read_bytes()
                ).decode(),
            }
        ],
    },
)["data"]
print(call("/api/v1/ingestion-runs/" + submission["workflow_id"]))
```

Poll the run until COMPLETED; its result includes document/ingestion/provenance IDs.
GET `/api/v1/documents/{id}/intelligence` exposes typed analyses, materializations,
media and provenance. POST `/api/v1/documents/{id}/verify` with `{}` compares live content;
HTTP 200 with `data.valid=false` means verification failed. Authentication/authorization
errors instead use canonical 401/403 error envelopes. No fake successful fallback occurs.

Collections accept `limit` and return `meta.next_cursor`; pass it unchanged as `cursor`.
Use `as_of` with an aware UTC timestamp: analyses/events use `available_at`, documents
use persistence `created_at`. Published time is never the knowledge cutoff. Entity/
media created times are applied where available; full mutable-link history is not reconstructed.

GET `/api/v1/search?q=Atlas`; GET `/api/v1/documents/{id}/similar?limit=5` for compatible
pgvector cosine top-k. The latter is API-only and exact scan, with lexical offline vectors.
Sources/events/entities and authorized audit are available through the same generated contracts.

```sh
uv run python scripts/export_schemas.py --check
pnpm web:api:check
```

Schema exports remain generated from the backend. Domain and OpenAPI contracts were
not redesigned in Phase 6. CI checks backend schema and frontend type drift.
