import json
from datetime import UTC, datetime

import pytest

from aegis.domain.ids import new_id
from aegis.domain.models import ProvenanceRecord
from aegis.provenance.service import ProvenanceService
from aegis.security.audit import AuditLog, MemoryAuditSink
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.keys import FileKeyProvider, generate_development_keys


@pytest.fixture
def service(tmp_path):
    generate_development_keys(tmp_path / "keys", "dev")
    return ProvenanceService(StandardCryptoProvider(FileKeyProvider(tmp_path / "keys")))


def test_signed_chain_and_content_verification(service):
    raw, normalized, artifact = new_id("raw"), new_id("doc"), "report:synthetic"
    analysis = new_id("ana")
    records = (
        ProvenanceRecord(
            provenance_id=new_id("prov"),
            subject_id=raw,
            input_ids=(),
            operation="raw",
            recorded_at=datetime.now(UTC),
            content_hash=service.crypto.hash(b"raw"),
        ),
        ProvenanceRecord(
            provenance_id=new_id("prov"),
            subject_id=normalized,
            input_ids=(raw,),
            operation="normalization",
            recorded_at=datetime.now(UTC),
            content_hash=service.crypto.hash(b"normalized"),
        ),
        ProvenanceRecord(
            provenance_id=new_id("prov"),
            subject_id=artifact,
            input_ids=(normalized,),
            operation="derived_artifact",
            analysis_id=analysis,
            recorded_at=datetime.now(UTC),
            content_hash=service.crypto.hash(b"artifact"),
        ),
    )
    manifest = service.sign(records, key_id="dev")
    evidence = {raw: b"raw", normalized: b"normalized", artifact: b"artifact"}
    result = service.verify(manifest, evidence)
    assert result.valid and result.content_verified
    assert not service.verify(manifest, {**evidence, raw: b"tampered"}).valid
    assert not service.verify(manifest, {}).content_verified
    assert not service.verify(manifest, {}).valid
    assert not service.verify(
        manifest.model_copy(update={"records": records[::-1]}), evidence
    ).valid
    changed = records[2].model_copy(update={"analysis_id": new_id("ana")})
    assert not service.verify(
        manifest.model_copy(update={"records": (*records[:2], changed)}), evidence
    ).valid
    with pytest.raises(ValueError):
        service.sign(records[1:], key_id="dev")


def test_audit_redaction_and_append_only():
    sink = MemoryAuditSink()
    audit = AuditLog(sink)
    audit.emit(
        "permission_denied",
        actor="synthetic",
        request_id="req",
        token="private-value",
        password="private-value",
        metadata={"authorization": "Bearer private-value", "nested": {"secret": "private-value"}},
    )
    event = sink.events[0]
    assert event.action == "permission_denied"
    assert "private-value" not in json.dumps(event.model_dump(mode="json"))
    assert isinstance(sink.events, tuple)
    with pytest.raises(ValueError):
        audit.emit("arbitrary log injection")
