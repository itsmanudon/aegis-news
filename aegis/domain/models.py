"""Canonical v1 records. No application, infrastructure or financial-signal imports."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from aegis.domain.ids import (
    AnalysisId,
    DocumentId,
    EntityId,
    IngestionId,
    MappingId,
    MediaId,
    MentionId,
    NewsEventId,
    ProvenanceId,
    RawObjectId,
    SourceId,
)

NonEmpty = Annotated[str, Field(min_length=1, max_length=512)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class DomainRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"


class Source(DomainRecord):
    source_id: SourceId
    name: NonEmpty
    kind: Literal["feed", "api", "upload", "web"]
    url: HttpUrl | None = None
    created_at: AwareDatetime


class ObjectReference(DomainRecord):
    bucket: NonEmpty
    key: NonEmpty
    sha256: Sha256
    size_bytes: int = Field(ge=0)
    content_type: NonEmpty


class RawIngestion(DomainRecord):
    ingestion_id: IngestionId
    source_id: SourceId
    raw_object_id: RawObjectId
    object: ObjectReference
    source_url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    first_seen_at: AwareDatetime
    ingested_at: AwareDatetime
    idempotency_key: NonEmpty

    @model_validator(mode="after")
    def check_time(self) -> Self:
        if self.ingested_at < self.first_seen_at:
            raise ValueError("ingested_at must not precede first_seen_at")
        return self


class MediaAsset(DomainRecord):
    media_id: MediaId
    ingestion_id: IngestionId
    kind: Literal["image", "audio", "video", "attachment"]
    object: ObjectReference
    created_at: AwareDatetime


class DocumentMediaLink(DomainRecord):
    document_id: DocumentId
    media_id: MediaId


class NewsDocument(DomainRecord):
    document_id: DocumentId
    ingestion_id: IngestionId
    source_id: SourceId
    title: NonEmpty
    text: str
    language: str | None = Field(default=None, min_length=2, max_length=35)
    published_at: AwareDatetime | None = None
    first_seen_at: AwareDatetime
    ingested_at: AwareDatetime
    created_at: AwareDatetime
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def check_time(self) -> Self:
        if self.ingested_at < self.first_seen_at or self.created_at < self.ingested_at:
            raise ValueError("document persistence times must be ordered")
        return self


class Entity(DomainRecord):
    entity_id: EntityId
    canonical_name: NonEmpty
    kind: Literal["organization", "person", "location", "other"]
    created_at: AwareDatetime


class EntityMention(DomainRecord):
    mention_id: MentionId
    document_id: DocumentId
    surface: NonEmpty
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    entity_id: EntityId | None = None
    evidence_kind: Literal["fact", "model_output"]
    analysis_id: AnalysisId | None = None

    @model_validator(mode="after")
    def check_evidence(self) -> Self:
        if self.end_offset <= self.start_offset:
            raise ValueError("mention offsets must form a nonempty span")
        if (self.evidence_kind == "model_output") != (self.analysis_id is not None):
            raise ValueError("model outputs require an analysis_id; facts must not have one")
        return self


class AssetMapping(DomainRecord):
    mapping_id: MappingId
    entity_id: EntityId
    scheme: Literal["exchange_symbol", "isin", "provider_id"]
    identifier: NonEmpty
    venue: NonEmpty | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def check_venue(self) -> Self:
        if self.scheme == "exchange_symbol" and self.venue is None:
            raise ValueError("exchange symbols require a venue")
        return self


class TopicResult(DomainRecord):
    result_type: Literal["topic"] = "topic"
    label: NonEmpty
    confidence: Confidence


class SentimentResult(DomainRecord):
    result_type: Literal["sentiment"] = "sentiment"
    label: Literal["positive", "neutral", "negative", "mixed"]
    score: float = Field(ge=-1, le=1, allow_inf_nan=False)
    confidence: Confidence
    entity_id: EntityId | None = None


class EntityResolutionResult(DomainRecord):
    result_type: Literal["entity_resolution"] = "entity_resolution"
    mention_id: MentionId
    entity_id: EntityId | None
    confidence: Confidence


class EntityExtractionResult(DomainRecord):
    result_type: Literal["entity_extraction"] = "entity_extraction"
    surface: NonEmpty
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    predicted_kind: Literal["organization", "person", "location", "other"] | None = None
    confidence: Confidence

    @model_validator(mode="after")
    def check_span(self) -> Self:
        if self.end_offset <= self.start_offset:
            raise ValueError("extraction offsets must form a nonempty span")
        return self


class EmbeddingResult(DomainRecord):
    result_type: Literal["embedding"] = "embedding"
    values: tuple[Annotated[float, Field(allow_inf_nan=False)], ...] = Field(min_length=1)


class EventExtractionResult(DomainRecord):
    result_type: Literal["event_extraction"] = "event_extraction"
    proposed_event_type: NonEmpty
    confidence: Confidence
    document_id: DocumentId
    evidence_text: str = Field(min_length=1)
    occurred_at: AwareDatetime | None = None


class EventClassificationResult(DomainRecord):
    result_type: Literal["event_classification"] = "event_classification"
    event_id: NewsEventId
    event_revision: int = Field(ge=1)
    label: NonEmpty
    confidence: Confidence


ModelOutput = Annotated[
    TopicResult
    | SentimentResult
    | EntityExtractionResult
    | EntityResolutionResult
    | EmbeddingResult
    | EventExtractionResult
    | EventClassificationResult,
    Field(discriminator="result_type"),
]


class AnalysisResult(DomainRecord):
    analysis_id: AnalysisId
    document_id: DocumentId
    analysis_type: Literal[
        "topic",
        "sentiment",
        "entity_extraction",
        "entity_resolution",
        "embedding",
        "event_extraction",
        "event_classification",
    ]
    provider: NonEmpty
    model_name: NonEmpty
    model_version: NonEmpty
    configuration_hash: Sha256
    created_at: AwareDatetime
    available_at: AwareDatetime
    outputs: tuple[ModelOutput, ...]

    @model_validator(mode="after")
    def check_outputs(self) -> Self:
        if self.available_at < self.created_at:
            raise ValueError("available_at must not precede created_at")
        if not self.outputs or any(o.result_type != self.analysis_type for o in self.outputs):
            raise ValueError("outputs must be nonempty and match analysis_type")
        if any(
            isinstance(o, EventExtractionResult) and o.document_id != self.document_id
            for o in self.outputs
        ):
            raise ValueError("event extraction evidence must reference the analyzed document")
        return self


class NewsEvent(DomainRecord):
    event_id: NewsEventId
    revision: int = Field(default=1, ge=1)
    summary: NonEmpty
    document_ids: tuple[DocumentId, ...] = Field(min_length=1)
    entity_ids: tuple[EntityId, ...] = ()
    occurred_at: AwareDatetime | None = None
    created_at: AwareDatetime
    available_at: AwareDatetime
    evidence_kind: Literal["fact", "model_output"]
    analysis_id: AnalysisId | None = None

    @model_validator(mode="after")
    def check_evidence(self) -> Self:
        if self.available_at < self.created_at:
            raise ValueError("available_at must not precede created_at")
        if (self.evidence_kind == "model_output") != (self.analysis_id is not None):
            raise ValueError("model outputs require an analysis_id; facts must not have one")
        return self


class ProvenanceRecord(DomainRecord):
    provenance_id: ProvenanceId
    subject_id: NonEmpty
    input_ids: tuple[NonEmpty, ...]
    operation: NonEmpty
    recorded_at: AwareDatetime
    content_hash: Sha256
    analysis_id: AnalysisId | None = None
