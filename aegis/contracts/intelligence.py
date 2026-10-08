"""Derived intelligence views; canonical assessments remain immutable domain records."""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, Field

from aegis.contracts.api import CollectionResponse, Contract
from aegis.domain.ids import AnalysisId
from aegis.domain.models import Confidence, NewsDocument, NonEmpty, Sha256, Source


class ModelIdentity(Contract):
    provider: NonEmpty
    model_name: NonEmpty
    model_version: NonEmpty
    configuration_hash: Sha256


class SnapshotCollectionResponse[T](CollectionResponse[T]):
    as_of: AwareDatetime


class TopicSummary(Contract):
    topic_id: str
    label: NonEmpty
    model: ModelIdentity
    document_count: int = Field(ge=0)
    first_available_at: AwareDatetime
    latest_available_at: AwareDatetime
    as_of: AwareDatetime
    selection_policy: str


class DocumentDiscoveryItem(Contract):
    document: NewsDocument
    source: Source


class TopicMembership(DocumentDiscoveryItem):
    analysis_id: AnalysisId
    confidence: Confidence
    available_at: AwareDatetime
    model: ModelIdentity


class CoverageBucket(Contract):
    day: date
    document_count: int = Field(ge=0)
    classified_count: int = Field(ge=0)


class SourceDistribution(Contract):
    source_id: str
    name: str
    document_count: int = Field(ge=0)


class SentimentDistribution(Contract):
    label: Literal["positive", "neutral", "negative", "mixed"]
    document_count: int = Field(ge=0)


class ModelDistribution(Contract):
    provider: str
    model_name: str
    model_version: str
    document_count: int = Field(ge=0)


class AnalyticsReport(Contract):
    start: AwareDatetime
    end: AwareDatetime
    as_of: AwareDatetime
    time_basis: Literal["published_at", "first_seen_at"]
    topic_id: str | None = None
    source_id: str | None = None
    population_count: int = Field(ge=0)
    classified_count: int = Field(ge=0)
    no_assessment_count: int = Field(ge=0)
    unknown_time_count: int = Field(ge=0)
    coverage: tuple[CoverageBucket, ...]
    sources: tuple[SourceDistribution, ...]
    sources_other_count: int = Field(ge=0)
    sentiment: tuple[SentimentDistribution, ...]
    models: tuple[ModelDistribution, ...]
    models_other_count: int = Field(ge=0)
    selection_policy: str
    limitations: tuple[str, ...]
