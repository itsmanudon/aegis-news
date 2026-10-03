"""Bounded development inputs. No worker-side paths or remote fetches."""

import base64
import binascii
import hashlib
import json
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from aegis.domain.ids import SourceId
from aegis.domain.models import NonEmpty

MAX_CONTENT_BYTES = 256 * 1024
MAX_MEDIA_BYTES = 256 * 1024
MAX_REQUEST_BYTES = 768 * 1024


class MediaInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["image", "attachment"]
    content_type: Literal["image/png", "image/jpeg", "application/pdf", "text/plain"]
    content_base64: str = Field(min_length=1, max_length=4 * ((MAX_MEDIA_BYTES + 2) // 3))

    @model_validator(mode="after")
    def compatible_kind(self) -> Self:
        if (self.kind == "image") != self.content_type.startswith("image/"):
            raise ValueError("media kind does not match MIME")
        return self


class IngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: SourceId
    idempotency_key: NonEmpty
    content_type: Literal["text/plain", "text/html", "application/json"] = "text/plain"
    content_base64: str = Field(min_length=1, max_length=4 * ((MAX_CONTENT_BYTES + 2) // 3))
    title: NonEmpty | None = None
    language: str | None = Field(default=None, min_length=2, max_length=35)
    published_at: AwareDatetime | None = None
    first_seen_at: AwareDatetime | None = None
    source_url: HttpUrl | None = None
    media: tuple[MediaInput, ...] = Field(default=(), max_length=4)
    correlation_id: str = Field(default="local-ingestion", min_length=1, max_length=128)

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must contain text")
        return value.strip() if value is not None else None


def decode_base64(value: str, limit: int) -> bytes:
    try:
        content = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid base64 content") from exc
    if not content or len(content) > limit:
        raise ValueError("content size outside allowed range")
    return content


def decode_content(request: IngestionRequest) -> bytes:
    if len(request.model_dump_json().encode()) > MAX_REQUEST_BYTES:
        raise ValueError("request exceeds Temporal payload budget")
    return decode_base64(request.content_base64, MAX_CONTENT_BYTES)


def decode_media(media: MediaInput) -> bytes:
    content = decode_base64(media.content_base64, MAX_MEDIA_BYTES)
    signatures = {
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
        "application/pdf": b"%PDF-",
    }
    signature = signatures.get(media.content_type)
    if signature and not content.startswith(signature):
        raise ValueError("content does not match declared MIME")
    if media.content_type == "text/plain":
        decoded = content.decode("utf-8-sig")
        if "\x00" in decoded:
            raise ValueError("binary content declared as text")
    return content


def fingerprint(request: IngestionRequest) -> str:
    """Identity includes exact bytes + all semantic metadata, excludes tracing only."""
    data = request.model_dump(mode="json", exclude={"correlation_id", "content_base64", "media"})
    data["content_sha256"] = hashlib.sha256(decode_content(request)).hexdigest()
    data["media"] = [
        {
            "kind": m.kind,
            "content_type": m.content_type,
            "sha256": hashlib.sha256(decode_media(m)).hexdigest(),
        }
        for m in request.media
    ]
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
