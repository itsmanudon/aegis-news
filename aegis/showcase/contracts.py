"""Allowlisted publication contract; private records cannot be passed through."""

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal, Self
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from aegis.domain.models import AnalysisResult, Sha256
from aegis.intelligence.taxonomy import EVENTS, TOPICS
from aegis.provenance.service import ProvenanceService, SignedManifest, canonical
from aegis.providers.models import canonical_url, safe_url
from aegis.security.crypto import StandardCryptoProvider
from aegis.showcase.daily_contracts import MediaLink, MetadataV2, TrustRegistry

SOURCES = {
    "nasa": "https://www.nasa.gov/feed/",
}
POLICY_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"
POLICY: Literal["nasa-metadata-only-v1"] = "nasa-metadata-only-v1"
MAX_EXPORT_BYTES = 8 * 1024 * 1024


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Metadata(PublicModel):
    id: Sha256
    source: Literal["nasa"]
    source_identity: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(max_length=2048)
    publisher: Literal["NASA"] = "NASA"
    published_at: AwareDatetime | None
    acquired_at: AwareDatetime
    rights: Literal["nasa-metadata-only-v1"] = POLICY

    @property
    def document_id(self) -> str:
        return "doc_" + str(uuid5(NAMESPACE_URL, self.source_identity))

    @model_validator(mode="after")
    def public_metadata(self) -> Self:
        if safe_url(self.url) != self.url or urlsplit(self.url).hostname not in {
            "www.nasa.gov",
            "science.nasa.gov",
        }:
            raise ValueError("source link must be an approved public NASA URL")
        if self.id != hashlib.sha256(canonical_url(self.url).encode()).hexdigest():
            raise ValueError("source identity hash mismatch")
        if not self.title.strip() or any(ord(c) < 32 for c in self.title):
            raise ValueError("invalid public headline")
        if self.source_identity != canonical_url(self.url):
            raise ValueError("source identity must be canonical URL")
        if self.acquired_at > datetime.now(UTC):
            raise ValueError("future acquisition time")
        return self


class PublicRecord(PublicModel):
    metadata: Metadata | MetadataV2
    analyses: tuple[AnalysisResult, ...] = Field(min_length=2, max_length=4)
    provenance: SignedManifest

    @model_validator(mode="after")
    def headline_evidence(self) -> Self:
        expected_models = {
            "topic": "keyword-topics",
            "sentiment": "lexicon-sentiment",
            "entity_extraction": "capitalized-spans",
            "event_extraction": "keyword-events",
        }
        tasks: set[str] = set()
        for analysis in self.analyses:
            if (
                analysis.analysis_type in tasks
                or analysis.model_name != expected_models.get(analysis.analysis_type)
                or analysis.document_id != self.metadata.document_id
                or analysis.model_version != "1"
                or analysis.provider != "local-baseline"
                or analysis.available_at < self.metadata.acquired_at
            ):
                raise ValueError("unsupported or inconsistent public analysis")
            tasks.add(analysis.analysis_type)
            if analysis.analysis_type in {"topic", "sentiment"} and len(analysis.outputs) != 1:
                raise ValueError("one topic and sentiment required per public record")
            for output in analysis.outputs:
                value = output.model_dump(mode="json")
                if output.result_type == "topic" and value["label"] not in TOPICS:
                    raise ValueError("unsupported public topic")
                if output.result_type == "sentiment" and value["entity_id"] is not None:
                    raise ValueError("no resolved entities in headline baseline")
                if output.result_type == "entity_extraction" and (
                    self.metadata.title[value["start_offset"] : value["end_offset"]]
                    != value["surface"]
                ):
                    raise ValueError("entity evidence must match public headline")
                if output.result_type == "event_extraction" and (
                    value["evidence_text"] not in self.metadata.title
                    or value["document_id"] != self.metadata.document_id
                    or value["proposed_event_type"] not in EVENTS
                    or value["occurred_at"] is not None
                ):
                    raise ValueError("event evidence must match public headline")
        if not {"topic", "sentiment"} <= tasks:
            raise ValueError("required public analysis missing")
        return self

    def contents(self) -> dict[str, bytes]:
        return {
            self.metadata.id: canonical(self.metadata.model_dump(mode="json")),
            self.metadata.id + ":analysis": canonical(
                [a.model_dump(mode="json") for a in self.analyses]
            ),
        }


class PublicExport(PublicModel):
    version: Literal["aegis-public-1"] = "aegis-public-1"
    exported_at: AwareDatetime
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    policy: Literal["nasa-metadata-only-v1"] = POLICY
    public_key: str = Field(min_length=44, max_length=44)
    key_id: Literal["showcase"] = "showcase"
    records: tuple[PublicRecord, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def complete(self) -> Self:
        if any(isinstance(r.metadata, MetadataV2) for r in self.records):
            raise ValueError("v2 metadata requires a versioned v2 export")
        if self.exported_at > datetime.now(UTC):
            raise ValueError("future export time")
        ids = [r.metadata.id for r in self.records]
        if len(ids) != len(set(ids)) or ids != sorted(ids):
            raise ValueError("records must have unique sorted source identities")
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(self.public_key, validate=True))
        crypto = StandardCryptoProvider(PublicKeys(key))
        service = ProvenanceService(crypto)
        for record in self.records:
            if record.metadata.acquired_at > self.exported_at:
                raise ValueError("export precedes acquisition")
            contents = record.contents()
            if (
                record.provenance.key_id != self.key_id
                or tuple(r.subject_id for r in record.provenance.records) != tuple(contents)
                or not service.verify(record.provenance, contents).valid
                or any(r.recorded_at > self.exported_at for r in record.provenance.records)
                or any(a.available_at > self.exported_at for a in record.analyses)
            ):
                raise ValueError("public signature, content or lineage verification failed")
        return self


class PublicKeys:
    """Verification adapter which has no secret key material."""

    def __init__(self, key: Ed25519PublicKey, key_id: str = "showcase") -> None:
        self.key = key
        self.key_id = key_id

    def verification_key(self, key_id: str) -> Ed25519PublicKey:
        if key_id != self.key_id:
            raise ValueError("untrusted key identifier")
        return self.key

    def encryption_key(self, key_id: str) -> bytes:
        raise ValueError("no encryption keys in publisher")

    def signing_key(self, key_id: str) -> Any:
        raise ValueError("no signing keys in publisher")

    def next_nonce(self, key_id: str) -> bytes:
        raise ValueError("no encryption in publisher")


class DailyExport(PublicModel):
    version: Literal["aegis-public-2"] = "aegis-public-2"
    exported_at: AwareDatetime
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    policy: Literal["curated-metadata-links-v2"] = "curated-metadata-links-v2"
    public_key: str
    key_id: str = Field(pattern=r"^daily-v[1-9][0-9]*$")
    trust: TrustRegistry
    parent_sha256: Sha256
    sequence: int = Field(ge=1)
    records: tuple[PublicRecord, ...] = Field(min_length=1, max_length=300)
    media: tuple[MediaLink, ...] = Field(default=(), max_length=12)
    release_signature: str = Field(min_length=88, max_length=88)

    @model_validator(mode="after")
    def verified_release(self) -> Self:
        primary = self.trust.keys.get(self.key_id)
        if not primary or primary.status != "active" or primary.public_key != self.public_key:
            raise ValueError("release signing key is not active")
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(self.public_key, validate=True))
        try:
            key.verify(
                base64.b64decode(self.release_signature, validate=True),
                canonical(self.model_dump(mode="json", exclude={"release_signature"})),
            )
        except InvalidSignature:
            raise ValueError("invalid signed public release envelope") from None
        ids = [r.metadata.id for r in self.records]
        if ids != sorted(set(ids)) or self.exported_at > datetime.now(UTC):
            raise ValueError("duplicate/unsorted records or future release")
        for record in self.records:
            identity = record.provenance.key_id
            entry = self.trust.keys.get(identity)
            if not entry or entry.status == "revoked":
                raise ValueError("untrusted or revoked record key")
            if isinstance(record.metadata, MetadataV2) and identity == "showcase":
                raise ValueError("new daily records cannot reuse the legacy local signing key")
            verification = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(entry.public_key, validate=True)
            )
            contents = record.contents()
            if (
                tuple(r.subject_id for r in record.provenance.records) != tuple(contents)
                or not ProvenanceService(StandardCryptoProvider(PublicKeys(verification, identity)))
                .verify(record.provenance, contents)
                .valid
                or record.metadata.acquired_at > self.exported_at
                or any(a.available_at > self.exported_at for a in record.analyses)
                or any(r.recorded_at > self.exported_at for r in record.provenance.records)
            ):
                raise ValueError("record content, lineage, time or signature verification failed")
        by_id = {r.metadata.id: r for r in self.records}
        if len({m.reference.id for m in self.media}) != len(self.media):
            raise ValueError("duplicate media identity")
        for item in self.media:
            if item.reference.refreshed_at > self.exported_at:
                raise ValueError("media refresh follows release")
            if len(set(item.record_ids)) != len(item.record_ids) or any(
                identity not in by_id
                or item.reference.relationship_term.casefold()
                not in by_id[identity].metadata.title.casefold()
                for identity in item.record_ids
            ):
                raise ValueError("media association must have matching public headline evidence")
        return self


Export = PublicExport | DailyExport


def parse_export(content: bytes) -> Export:
    if not content or len(content) > MAX_EXPORT_BYTES:
        raise ValueError("export size exceeds publication boundary")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON field")
            value[key] = item
        return value

    value = json.loads(content, object_pairs_hook=unique)
    if isinstance(value, dict) and value.get("version") == "aegis-public-2":
        return DailyExport.model_validate(value)
    return PublicExport.model_validate(value)
