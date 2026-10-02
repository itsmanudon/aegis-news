"""Versioned asynchronous messages, separate from canonical NewsEvent records."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from aegis.domain.ids import (
    AnalysisId,
    DocumentId,
    EntityId,
    IngestionId,
    MentionId,
    MessageId,
    NewsEventId,
)
from aegis.domain.models import DomainRecord, NonEmpty


class DocumentIngested(DomainRecord):
    document_id: DocumentId
    ingestion_id: IngestionId


class DocumentNormalized(DomainRecord):
    document_id: DocumentId
    revision: int = Field(ge=1)


class AnalysisCompleted(DomainRecord):
    analysis_id: AnalysisId
    document_id: DocumentId
    available_at: AwareDatetime


class EntityResolved(DomainRecord):
    entity_id: EntityId
    mention_id: MentionId
    analysis_id: AnalysisId


class NewsEventChanged(DomainRecord):
    event_id: NewsEventId
    revision: int = Field(ge=1)
    available_at: AwareDatetime


class IntegrityFailed(DomainRecord):
    subject_id: NonEmpty
    reason_code: NonEmpty


class EventEnvelope(DomainRecord):
    event_id: MessageId
    event_type: NonEmpty
    event_version: Literal["1"] = "1"
    occurred_at: AwareDatetime
    producer: NonEmpty
    correlation_id: str = Field(min_length=1, max_length=128)
    idempotency_key: NonEmpty


class DocumentIngestedEvent(EventEnvelope):
    event_type: Literal["document.ingested.v1"] = "document.ingested.v1"
    data: DocumentIngested


class DocumentNormalizedEvent(EventEnvelope):
    event_type: Literal["document.normalized.v1"] = "document.normalized.v1"
    data: DocumentNormalized


class AnalysisCompletedEvent(EventEnvelope):
    event_type: Literal["analysis.completed.v1"] = "analysis.completed.v1"
    data: AnalysisCompleted


class EntityResolvedEvent(EventEnvelope):
    event_type: Literal["entity.resolved.v1"] = "entity.resolved.v1"
    data: EntityResolved


class NewsEventCreatedEvent(EventEnvelope):
    event_type: Literal["news.event.created.v1"] = "news.event.created.v1"
    data: NewsEventChanged


class NewsEventUpdatedEvent(EventEnvelope):
    event_type: Literal["news.event.updated.v1"] = "news.event.updated.v1"
    data: NewsEventChanged


class IntegrityFailedEvent(EventEnvelope):
    event_type: Literal["integrity.failed.v1"] = "integrity.failed.v1"
    data: IntegrityFailed


AsyncEvent = Annotated[
    DocumentIngestedEvent
    | DocumentNormalizedEvent
    | AnalysisCompletedEvent
    | EntityResolvedEvent
    | NewsEventCreatedEvent
    | NewsEventUpdatedEvent
    | IntegrityFailedEvent,
    Field(discriminator="event_type"),
]
EVENT_MODELS = (
    DocumentIngestedEvent,
    DocumentNormalizedEvent,
    AnalysisCompletedEvent,
    EntityResolvedEvent,
    NewsEventCreatedEvent,
    NewsEventUpdatedEvent,
    IntegrityFailedEvent,
)
