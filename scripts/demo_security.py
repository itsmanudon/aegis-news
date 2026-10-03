"""Automate local security evidence; every controlled content change is restored."""

import argparse
import asyncio
import base64
import json
import logging
import sys
import urllib.error
from typing import Any

from cryptography.exceptions import InvalidTag

from aegis.ingestion.runtime import make_service
from aegis.intelligence.pipeline import AnalysisPipeline
from aegis.observability.logging import JsonFormatter
from aegis.persistence.models import DocumentRow
from aegis.provenance.service import ProvenanceService, canonical
from aegis.security.audit import AuditLog, MemoryAuditSink
from aegis.security.crypto import EncryptedPayload, Signature, StandardCryptoProvider
from aegis.security.dev_identity import issue_development_token
from scripts.demo_seed import DemoClient


async def scenario(url: str, hold_tamper_seconds: int = 0) -> dict[str, Any]:
    api = DemoClient(url)
    service = make_service(api.settings)
    crypto = StandardCryptoProvider(api.keys)
    pipeline = AnalysisPipeline(service.repository, ProvenanceService(crypto), "local")
    checks: list[str] = []

    def denied(path: str, role: str | None, code: int, body: Any = None) -> None:
        try:
            api.request(path, body, role)
        except urllib.error.HTTPError as exc:
            assert exc.code == code
        else:
            raise AssertionError("Protected request unexpectedly succeeded")

    try:
        denied("/api/v1/documents", None, 401)
        checks.append("authentication_required")
        assert api.request("/api/v1/security/me", role="analyst")["data"]["scopes"]
        checks.append("authorized_scopes")
        denied("/api/v1/ingestions", "viewer", 403, {})
        denied("/api/v1/security/audit", "analyst", 403)
        checks.append("insufficient_scope_denied")
        sources = api.request("/api/v1/sources?limit=100")["data"]
        source = next(s for s in sources if s["name"] == "CC0 presentation demo v1")
        documents = api.request("/api/v1/documents?limit=100&source_id=" + source["source_id"])[
            "data"
        ]
        document = (
            next(
                d
                for d in documents
                if d["document"]["title"] == "Atlas Labs reports growth and merger"
            )
            if documents and "document" in documents[0]
            else next(d for d in documents if d["title"] == "Atlas Labs reports growth and merger")
        )
        identity = (
            document["document"]["document_id"]
            if "document" in document
            else document["document_id"]
        )
        view = api.request(f"/api/v1/documents/{identity}/intelligence")["data"]
        ingestion = service.repository.get_ingestion(view["document"]["ingestion_id"])
        raw = await service.storage.get_object(ingestion.object.key)
        assert crypto.hash(raw) == ingestion.object.sha256
        checks.append("sha256_raw_integrity")

        def verify() -> bool:
            return bool(
                api.request(f"/api/v1/documents/{identity}/verify", {}, "analyst")["data"]["valid"]
            )

        assert verify()
        checks.append("live_provenance_verified")
        try:
            await service.storage.put_object(
                ingestion.object.key, raw + b"controlled-tamper", ingestion.object.content_type
            )
            assert not verify()
            if hold_tamper_seconds:
                print(
                    "Controlled raw tampering detected; restoration follows automatically.",
                    file=sys.stderr,
                )
                await asyncio.sleep(hold_tamper_seconds)
        finally:
            await service.storage.put_object(
                ingestion.object.key, raw, ingestion.object.content_type
            )
        assert verify()
        checks.append("raw_object_tampering_detected_and_restored")
        original_text = view["document"]["text"]
        try:
            with service.repository.sessions.begin() as session:
                row = session.get(DocumentRow, identity)
                assert row is not None
                row.text = original_text + " controlled-tamper"
            assert not verify()
        finally:
            with service.repository.sessions.begin() as session:
                row = session.get(DocumentRow, identity)
                assert row is not None
                row.text = original_text
        assert verify()
        checks.append("database_document_tampering_detected_and_restored")
        assert view["media"] and view["media"][0]["kind"] == "image"
        media = view["media"][0]["object"]
        image = await service.storage.get_object(media["key"])
        try:
            await service.storage.put_object(
                media["key"], image + b"controlled-tamper", media["content_type"]
            )
            assert not verify()
        finally:
            await service.storage.put_object(media["key"], image, media["content_type"])
        assert verify()
        checks.append("linked_image_tampering_detected_and_restored")
        manifest = pipeline.manifest(identity)
        provenance_id = next(
            r.provenance_id for r in manifest.records if r.operation == "normalization"
        )
        archive = EncryptedPayload.model_validate_json(
            await service.storage.get_object(f"provenance/encrypted/{provenance_id}.json")
        )
        # The storage key uses the run-level provenance ID returned by the workflow.
        if not archive.ciphertext:
            raise AssertionError("Empty encrypted archive")
        assert (
            json.loads(crypto.decrypt(archive, associated_data=identity.encode()))["signature"]
            == manifest.signature
        )
        checks.append("aes256gcm_decryption")
        damaged = archive.model_copy(
            update={"ciphertext": bytes([archive.ciphertext[0] ^ 1]) + archive.ciphertext[1:]}
        )
        try:
            crypto.decrypt(damaged, associated_data=identity.encode())
        except InvalidTag:
            pass
        else:
            raise AssertionError("Modified ciphertext was accepted")
        checks.append("aes256gcm_modified_ciphertext_rejected")
        signed_content = canonical(manifest.model_dump(mode="json", exclude={"signature"}))
        signature = Signature(
            key_id=manifest.key_id, algorithm="Ed25519", value=base64.b64decode(manifest.signature)
        )
        assert crypto.verify(signed_content, signature)
        checks.append("ed25519_signature_verified")
        assert not crypto.verify(signed_content + b"modified", signature)
        checks.append("ed25519_modified_content_rejected")
        audit = api.request("/api/v1/security/audit?limit=100")["data"]
        assert any(e["action"] == "permission_denied" for e in audit)
        assert any(
            e["action"] == "integrity_verification" and e["outcome"] == "failure" for e in audit
        )
        checks.append("persistent_audit_events")
        token = issue_development_token(
            api.settings, api.keys, key_id="local", subject="redaction-check", role="analyst"
        )
        record = logging.LogRecord(
            "demo.redaction",
            logging.INFO,
            "",
            0,
            "Bearer " + token + " password=demo-marker",
            (),
            None,
        )
        formatted = JsonFormatter().format(record)
        assert token not in formatted and "demo-marker" not in formatted
        sink = MemoryAuditSink()
        AuditLog(sink).emit("security_change", outcome="success", token=token, secret="demo-marker")
        assert (
            token not in sink.events[0].model_dump_json()
            and "demo-marker" not in sink.events[0].model_dump_json()
        )
        checks.append("log_and_audit_secret_redaction")
        return {
            "result": "passed",
            "checks": checks,
            "document_id": identity,
            "media_id": view["media"][0]["media_id"],
            "final_verification": "valid",
            "scope": (
                "Controlled local synthetic data only; source text/object/image restored "
                "in finally blocks; no tokens or key bytes exported"
            ),
        }
    finally:
        service.repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://api:8000")
    parser.add_argument(
        "--hold-tamper-seconds",
        type=int,
        choices=range(31),
        default=0,
        metavar="0..30",
        help="Briefly hold raw tampering for the live UI; always restore",
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(scenario(args.api_url, args.hold_tamper_seconds)), indent=2))


if __name__ == "__main__":
    main()
