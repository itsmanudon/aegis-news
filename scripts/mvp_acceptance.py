"""Safe local acceptance scenario. Uses synthetic samples and restores deliberate tampering."""

import argparse
import asyncio
import base64
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from aegis.domain.models import Entity
from aegis.ingestion.runtime import make_service
from aegis.intelligence.pipeline import stable_id
from aegis.persistence.models import EntityRow
from aegis.security.crypto import EncryptedPayload, StandardCryptoProvider
from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider
from aegis.settings import get_settings


async def scenario(api_url: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.environment == "production" or not settings.dev_identity_enabled:
        raise ValueError("Acceptance writes and tampering are restricted to local development")
    keys = FileKeyProvider(settings.security_key_directory)

    def token(role: str) -> str:
        return issue_development_token(
            settings, keys, key_id=settings.provenance_key_id, subject="mvp-acceptance", role=role
        )

    def request(path: str, body: Any = None, role: str = "admin") -> dict[str, Any]:
        req = urllib.request.Request(
            api_url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + token(role), "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            result: dict[str, Any] = json.load(response)
            return result

    assert request("/health")["data"]["status"] == "ok"
    assert request("/ready")["data"]["status"] == "ready"
    assert request("/api/v1/security/me", role="analyst")["data"]["subject"] == "mvp-acceptance"
    source = request(
        "/api/v1/sources", {"name": "Synthetic MVP " + uuid4().hex[:8], "kind": "upload"}
    )["data"]
    samples = json.loads(
        (Path(__file__).resolve().parents[1] / "data/samples/mvp.json").read_text()
    )
    service = make_service(settings)
    try:
        # Curated synthetic identities are seeded independently; NER never creates entities.
        with service.repository.sessions.begin() as session:
            for sample in samples:
                identity = stable_id("ent", "demo:" + sample["entity"])
                if session.get(EntityRow, identity) is None:
                    entity = Entity(
                        entity_id=identity,
                        canonical_name=sample["entity"],
                        kind=sample["kind"],
                        created_at=datetime.now(UTC),
                    )
                    session.add(EntityRow(**entity.model_dump()))
        items = []
        for index, sample in enumerate(samples):
            article = {k: sample[k] for k in ("title", "text", "published_at")}
            article["language"] = "en"
            item = dict(
                source_id=source["source_id"],
                idempotency_key=f"mvp-{index}",
                content_type="application/json",
                content_base64=base64.b64encode(json.dumps(article).encode()).decode(),
                correlation_id="mvp-acceptance",
            )
            if sample.get("media"):
                item["media"] = [
                    {
                        "kind": "attachment",
                        "content_type": "text/plain",
                        "content_base64": base64.b64encode(
                            b"Synthetic workshop programme, CC0."
                        ).decode(),
                    }
                ]
            items.append(item)
        submissions = request("/api/v1/ingestions/batch", {"items": items})["data"]["submissions"]
        duplicate = request("/api/v1/ingestions", items[0])["data"]
        assert duplicate["workflow_id"] == submissions[0]["workflow_id"]
        completed = []
        for submission in submissions:
            deadline = time.monotonic() + 180
            while True:
                run = request("/api/v1/ingestion-runs/" + submission["workflow_id"])["data"]
                if run["status"] == "COMPLETED":
                    completed.append(run["result"])
                    break
                if (
                    run["status"] in {"FAILED", "TIMED_OUT", "TERMINATED", "CANCELED"}
                    or time.monotonic() > deadline
                ):
                    raise AssertionError(f"workflow did not complete: {run}")
                await asyncio.sleep(1)
        for result in completed:
            identity = result["document_id"]
            view = request(f"/api/v1/documents/{identity}/intelligence", role="analyst")["data"]
            assert {v["analysis_type"] for v in view["analyses"]} >= {
                "topic",
                "sentiment",
                "embedding",
                "entity_extraction",
                "event_extraction",
                "entity_resolution",
            }
            assert view["entities"] and view["events"] and view["provenance"]
            assert request(f"/api/v1/documents/{identity}/verify", {}, "analyst")["data"]["valid"]
        assert view["media"]
        first = completed[0]["document_id"]
        assert request("/api/v1/search?q=Atlas", role="analyst")["data"]
        assert request(f"/api/v1/documents/{first}/similar", role="analyst")["data"]
        assert request("/api/v1/events", role="analyst")["data"]
        assert request("/api/v1/entities", role="analyst")["data"]
        cutoff = request("/api/v1/documents?as_of=2021-01-01T00%3A00%3A00Z", role="analyst")["data"]
        assert not any(value["document_id"] == first for value in cutoff)
        try:
            request("/api/v1/ingestions", items[0], "viewer")
            raise AssertionError("viewer was allowed to ingest")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        ingestion = service.repository.get_ingestion(completed[0]["ingestion_id"])
        raw = await service.storage.get_object(ingestion.object.key)
        assert StandardCryptoProvider(keys).hash(raw) == ingestion.object.sha256
        try:
            await service.storage.put_object(
                ingestion.object.key, raw + b"tampered", ingestion.object.content_type
            )
            assert not request(f"/api/v1/documents/{first}/verify", {}, "analyst")["data"]["valid"]
        finally:
            await service.storage.put_object(
                ingestion.object.key, raw, ingestion.object.content_type
            )
        assert request(f"/api/v1/documents/{first}/verify", {}, "analyst")["data"]["valid"]
        archive = await service.storage.get_object(
            f"provenance/encrypted/{completed[0]['provenance_id']}.json"
        )
        payload = EncryptedPayload.model_validate_json(archive)
        assert payload.algorithm == "AES-256-GCM"
        assert json.loads(
            StandardCryptoProvider(keys).decrypt(payload, associated_data=first.encode())
        )["signature"]
        assert request("/api/v1/security/audit")["data"]
        with urllib.request.urlopen(api_url + "/metrics", timeout=10) as response:
            assert b"aegis_http_requests_total" in response.read()
        return {
            "result": "passed",
            "documents": completed,
            "source_id": source["source_id"],
            "checks": [
                "development_identity",
                "source_creation",
                "batch_ingestion",
                "duplicate",
                "temporal",
                "raw_storage",
                "media",
                "offline_ai",
                "immutable_analyses",
                "entities",
                "events",
                "search",
                "pgvector_similarity",
                "as_of",
                "sha256",
                "ed25519",
                "aes256gcm",
                "provenance",
                "permission_denied",
                "tampering_detected_and_restored",
                "audit",
                "metrics",
            ],
        }
    finally:
        service.repository.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://api:8000")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(scenario(args.api_url)), indent=2))


if __name__ == "__main__":
    main()
