"""Signed internal lineage manifests, deliberately not a C2PA implementation."""

import base64
import json
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from aegis.domain.models import ProvenanceRecord
from aegis.security.crypto import CryptoProvider, Signature


class ManifestStore(Protocol):
    def append(
        self, manifest_hash: str, manifest: dict[str, Any], key_id: str, created_at: datetime
    ) -> None: ...


class SignedManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = "aegis-provenance-1"
    records: tuple[ProvenanceRecord, ...] = Field(min_length=1, max_length=100)
    chain_hashes: tuple[str, ...]
    key_id: str
    signature: str  # Base64, never a private key.


class VerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    valid: bool
    signature_valid: bool
    chain_valid: bool
    content_verified: bool
    reason: str


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


class ProvenanceService:
    def __init__(self, crypto: CryptoProvider, store: ManifestStore | None = None) -> None:
        self.crypto = crypto
        self.store = store

    def _chain(self, records: tuple[ProvenanceRecord, ...]) -> tuple[str, ...]:
        if (
            not records
            or len(records) > 100
            or records[0].operation != "raw"
            or records[0].input_ids
        ):
            raise ValueError("Chain must begin with raw content")
        seen: set[str] = set()
        ids: set[str] = set()
        hashes: list[str] = []
        previous = "0" * 64
        for index, record in enumerate(records):
            if record.subject_id in seen or record.provenance_id in ids:
                raise ValueError("Duplicate lineage identifier")
            if index and (not record.input_ids or any(i not in seen for i in record.input_ids)):
                raise ValueError("Missing or forward lineage input")
            if record.operation == "derived_artifact" and record.analysis_id is None:
                raise ValueError("Derived artifact requires an analysis reference")
            previous = self.crypto.hash(
                canonical({"previous": previous, "record": record.model_dump(mode="json")})
            )
            hashes.append(previous)
            seen.add(record.subject_id)
            ids.add(record.provenance_id)
        return tuple(hashes)

    def _body(self, manifest: SignedManifest) -> bytes:
        return canonical(manifest.model_dump(mode="json", exclude={"signature"}))

    def sign(self, records: tuple[ProvenanceRecord, ...], *, key_id: str) -> SignedManifest:
        manifest = SignedManifest(
            records=records, chain_hashes=self._chain(records), key_id=key_id, signature=""
        )
        signature = self.crypto.sign(self._body(manifest), key_id=key_id)
        manifest = manifest.model_copy(
            update={"signature": base64.b64encode(signature.value).decode("ascii")}
        )
        if self.store:
            self.store.append(
                self.crypto.hash(self._body(manifest)),
                manifest.model_dump(mode="json"),
                key_id,
                datetime.now(UTC),
            )
        return manifest

    def verify(self, manifest: SignedManifest, contents: dict[str, bytes]) -> VerificationResult:
        try:
            chain_valid = (
                manifest.version == "aegis-provenance-1"
                and self._chain(manifest.records) == manifest.chain_hashes
            )
        except ValueError:
            chain_valid = False
        try:
            signature_valid = self.crypto.verify(
                self._body(manifest),
                Signature(
                    key_id=manifest.key_id,
                    algorithm="Ed25519",
                    value=base64.b64decode(manifest.signature, validate=True),
                ),
            )
        except ValueError:
            signature_valid = False
        content_verified = all(
            record.subject_id in contents
            and self.crypto.hash(contents[record.subject_id]) == record.content_hash
            for record in manifest.records
        )
        valid = chain_valid and signature_valid and content_verified
        return VerificationResult(
            valid=valid,
            signature_valid=signature_valid,
            chain_valid=chain_valid,
            content_verified=content_verified,
            reason="verified" if valid else "verification_failed",
        )
