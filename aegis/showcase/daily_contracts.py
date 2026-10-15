"""Versioned public metadata and multimedia; v1 bytes remain unchanged."""

import base64
import hashlib
import re
from datetime import UTC, datetime
from typing import Literal, Self
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from aegis.domain.models import Sha256
from aegis.providers.models import canonical_url, safe_url
from aegis.showcase.sources import REGISTRY, approved_link


class StrictPublic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def public_text(value: str) -> bool:
    return bool(value.strip()) and len(value) <= 512 and not any(ord(c) < 32 for c in value)


class MediaReference(StrictPublic):
    id: Sha256
    kind: Literal["image", "video"]
    title: str = Field(min_length=1, max_length=512)
    source_url: str = Field(max_length=2048)
    asset_url: str | None = Field(default=None, max_length=2048)
    creator: str = Field(min_length=1, max_length=512)
    license: Literal["Public Domain", "CC BY 4.0", "CC BY-SA 4.0", "CC0", "NASA Reference Only"]
    license_url: str = Field(max_length=2048)
    alt: str = Field(min_length=1, max_length=512)
    relationship: Literal["context"] = "context"
    relationship_term: str = Field(min_length=3, max_length=64)
    acquired_at: AwareDatetime
    refreshed_at: AwareDatetime
    published_at: AwareDatetime | None = None
    created_at: AwareDatetime | None = None
    status: Literal["referenced"] = "referenced"
    platform_id: str = Field(min_length=1, max_length=256)
    publisher: Literal["Wikimedia Commons", "NASA Image and Video Library"]

    @model_validator(mode="after")
    def rights_and_origins(self) -> Self:
        for value in (self.source_url, self.license_url, self.asset_url):
            clean = value.split("#", 1)[0] if value else value
            if value is not None and safe_url(clean) != clean:
                raise ValueError("unsafe media reference")
        if self.id != hashlib.sha256(self.source_url.encode()).hexdigest():
            raise ValueError("media identity mismatch")
        if not all(public_text(v) for v in (self.title, self.creator, self.alt)):
            raise ValueError("invalid media text")
        if self.acquired_at > self.refreshed_at or self.refreshed_at > datetime.now(UTC):
            raise ValueError("invalid media timestamps")
        if self.relationship_term.casefold() not in self.title.casefold():
            raise ValueError("media title does not support context relationship")
        if self.kind == "image":
            if (
                self.publisher != "Wikimedia Commons"
                or urlsplit(self.source_url).hostname != "commons.wikimedia.org"
                or not self.asset_url
                or urlsplit(self.asset_url).hostname
                not in {"upload.wikimedia.org", "thumb.wikimedia.org"}
                or self.license == "NASA Reference Only"
                or urlsplit(self.license_url).hostname
                not in {"creativecommons.org", "commons.wikimedia.org"}
            ):
                raise ValueError("image lacks approved item rights or origin")
        elif (
            self.publisher != "NASA Image and Video Library"
            or urlsplit(self.source_url).hostname != "images.nasa.gov"
            or self.asset_url is not None
            or self.license != "NASA Reference Only"
            or self.license_url != "https://www.nasa.gov/nasa-brand-center/images-and-media/"
        ):
            raise ValueError("video must remain an official external NASA reference")
        return self


class MetadataV2(StrictPublic):
    schema_version: Literal["2"] = "2"
    id: Sha256
    source: str = Field(min_length=1, max_length=64)
    source_identity: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(max_length=2048)
    publisher: str = Field(min_length=1, max_length=512)
    published_at: AwareDatetime | None
    discovered_at: AwareDatetime | None = None
    occurred_at: AwareDatetime | None = None
    source_updated_at: AwareDatetime | None = None
    acquired_at: AwareDatetime
    source_categories: tuple[str, ...] = Field(default=(), max_length=12)
    publisher_country: str | None = Field(default=None, max_length=64)
    rights: Literal["metadata-links-v2"] = "metadata-links-v2"

    @property
    def document_id(self) -> str:
        return "doc_" + str(uuid5(NAMESPACE_URL, self.source_identity))

    @model_validator(mode="after")
    def approved(self) -> Self:
        if not approved_link(self.source, self.url):
            raise ValueError("unapproved source or source URL")
        if self.source != "gdelt" and self.publisher != REGISTRY[self.source].name:
            raise ValueError("publisher attribution does not match source")
        if self.source_identity != canonical_url(self.url):
            raise ValueError("canonical identity mismatch")
        if self.id != hashlib.sha256(self.source_identity.encode()).hexdigest():
            raise ValueError("source identity hash mismatch")
        if not all(public_text(v) for v in (self.title, self.publisher, *self.source_categories)):
            raise ValueError("invalid public metadata text")
        if self.acquired_at > datetime.now(UTC):
            raise ValueError("future acquisition time")
        if self.published_at and self.published_at > self.acquired_at:
            raise ValueError("publication cannot be in the future at acquisition")
        if self.discovered_at and self.discovered_at > self.acquired_at:
            raise ValueError("provider discovery cannot follow acquisition")
        if any(
            value and value > self.acquired_at
            for value in (self.occurred_at, self.source_updated_at)
        ):
            raise ValueError("event/source update cannot follow acquisition")
        return self


class MediaLink(StrictPublic):
    reference: MediaReference
    record_ids: tuple[Sha256, ...] = Field(min_length=1, max_length=12)


class KeyEntry(StrictPublic):
    public_key: str
    status: Literal["active", "verify-only", "revoked"]

    @model_validator(mode="after")
    def valid(self) -> Self:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(self.public_key, validate=True))
        return self


class TrustRegistry(StrictPublic):
    version: Literal["aegis-public-trust-2"] = "aegis-public-trust-2"
    keys: dict[str, KeyEntry] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def key_names(self) -> Self:
        if any(not re.fullmatch(r"showcase|daily-v[1-9][0-9]*", key) for key in self.keys):
            raise ValueError("invalid publication key identifier")
        return self
