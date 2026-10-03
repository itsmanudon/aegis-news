"""Activity-facing ingestion pipeline, independent of Temporal and API transport."""

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

from aegis.domain.models import NewsDocument, ObjectReference
from aegis.ingestion.inputs import IngestionRequest, decode_content, decode_media, fingerprint
from aegis.ingestion.repository import IngestionRepository
from aegis.media.storage import ObjectStorage
from aegis.normalization.article import parse_article


class IngestionService:
    def __init__(
        self, repository: IngestionRepository, storage: ObjectStorage, bucket: str
    ) -> None:
        self.repository, self.storage, self.bucket = repository, storage, bucket

    async def store(self, content: bytes, mime: str, prefix: str) -> ObjectReference:
        digest = hashlib.sha256(content).hexdigest()
        mime_digest = hashlib.sha256(mime.encode()).hexdigest()[:16]
        key = f"ingestion/v1/{prefix}/{digest[:2]}/{digest}/{mime_digest}"
        if await self.storage.exists(key):
            existing = await self.storage.get_object(key)
            metadata = await self.storage.metadata(key)
            if (
                hashlib.sha256(existing).hexdigest() != digest
                or metadata.size_bytes != len(content)
                or metadata.content_type != mime
            ):
                raise ValueError("stored object hash or metadata integrity conflict")
        else:
            await self.storage.put_object(key, content, mime)
        return ObjectReference(
            bucket=self.bucket, key=key, sha256=digest, size_bytes=len(content), content_type=mime
        )

    async def prepare(
        self,
        request: IngestionRequest,
        observed_at: datetime | None = None,
    ) -> str:
        observed_at = observed_at or datetime.now(UTC)
        content = decode_content(request)
        article = parse_article(content, request.content_type)
        # Validate all attachments before any object side effect.
        media_bytes = [decode_media(m) for m in request.media]
        digest = fingerprint(request)
        await asyncio.to_thread(self.repository.get_source, request.source_id)
        existing = await asyncio.to_thread(
            self.repository.find_retry,
            request.source_id,
            request.idempotency_key,
            digest,
        )
        if existing:
            return existing
        if request.first_seen_at and request.first_seen_at > datetime.now(UTC):
            raise ValueError("first_seen_at is in the future")
        raw = await self.store(content, request.content_type, "raw")
        media: list[dict[str, Any]] = []
        for item, content in zip(request.media, media_bytes, strict=True):
            ref = await self.store(content, item.content_type, "media")
            media.append({"kind": item.kind, "object": ref.model_dump(mode="json")})
        return await asyncio.to_thread(
            self.repository.persist_ingestion,
            request,
            digest,
            raw,
            media,
            request.published_at if request.published_at is not None else article.published_at,
            observed_at,
        )

    async def normalize(self, ingestion_id: str) -> NewsDocument:
        ingestion, document_id, metadata = await asyncio.to_thread(
            self.repository.normalization_context,
            ingestion_id,
        )
        content = await self.storage.get_object(ingestion.object.key)
        if hashlib.sha256(content).hexdigest() != ingestion.object.sha256:
            raise ValueError("raw object hash integrity failure")
        article = parse_article(content, ingestion.object.content_type)
        return NewsDocument(
            document_id=document_id,
            ingestion_id=ingestion_id,
            source_id=ingestion.source_id,
            title=metadata.get("title") or article.title,
            text=article.text,
            language=metadata.get("language") or article.language,
            published_at=ingestion.published_at,
            first_seen_at=ingestion.first_seen_at,
            ingested_at=ingestion.ingested_at,
            created_at=max(datetime.now(UTC), ingestion.ingested_at),
            revision=1,
        )

    def complete(self, ingestion_id: str, document: NewsDocument) -> NewsDocument:
        return self.repository.complete(ingestion_id, document)
