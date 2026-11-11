"""Incremental document feed for a downstream consumer that syncs on a schedule.

A bundle carries what the consumer stores about one document and nothing it must not:
no article text, no evidence excerpts, no embeddings.
"""

from typing import Literal

from pydantic import AwareDatetime, Field, HttpUrl

from aegis.contracts.api import Contract, CursorPagination, ResponseMeta
from aegis.domain.ids import (
    AnalysisId,
    DocumentId,
    EntityId,
    IngestionId,
    MappingId,
    NewsEventId,
    SourceId,
)
from aegis.domain.models import AnalysisResult, Confidence, NonEmpty, Sha256, Source


class FeedDocument(Contract):
    document_id: DocumentId
    ingestion_id: IngestionId
    source_id: SourceId
    title: NonEmpty
    url: HttpUrl | None
    language: str | None
    published_at: AwareDatetime | None
    first_seen_at: AwareDatetime
    ingested_at: AwareDatetime
    created_at: AwareDatetime
    available_at: AwareDatetime
    last_signed_at: AwareDatetime
    revision: int = Field(ge=1)


class FeedInstrument(Contract):
    entity_id: EntityId
    canonical_name: NonEmpty
    kind: Literal["organization", "person", "location", "other"]
    mapping_id: MappingId
    scheme: Literal["exchange_symbol", "isin", "provider_id"]
    identifier: NonEmpty
    venue: NonEmpty | None
    resolution_analysis_id: AnalysisId
    confidence: Confidence


class FeedEvent(Contract):
    event_id: NewsEventId
    revision: int = Field(ge=1)
    event_type: NonEmpty | None
    confidence: Confidence | None
    occurred_at: AwareDatetime | None
    created_at: AwareDatetime
    available_at: AwareDatetime
    evidence_kind: Literal["fact", "model_output"]
    analysis_id: AnalysisId | None


class FeedManifest(Contract):
    manifest_hash: Sha256
    key_id: NonEmpty
    signed_at: AwareDatetime


class FeedItem(Contract):
    document: FeedDocument
    source: Source
    analyses: tuple[AnalysisResult, ...]
    instruments: tuple[FeedInstrument, ...]
    events: tuple[FeedEvent, ...]
    manifests: tuple[FeedManifest, ...]


class FeedResponse(Contract):
    data: tuple[FeedItem, ...]
    as_of: AwareDatetime
    pagination: CursorPagination
    resume_cursor: str = Field(min_length=1)
    meta: ResponseMeta
