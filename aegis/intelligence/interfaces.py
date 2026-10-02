"""Typed model ports. No models, providers, inference or downloads in this phase."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from aegis.domain.ids import DocumentId
from aegis.domain.models import AnalysisResult, Entity, EntityMention, NewsDocument, NewsEvent


class SentimentAnalyzer(Protocol):
    async def analyze(self, document: NewsDocument) -> AnalysisResult: ...


class TopicClassifier(Protocol):
    async def classify(self, document: NewsDocument) -> AnalysisResult: ...


class EntityExtractor(Protocol):
    async def extract(self, document: NewsDocument) -> tuple[EntityMention, ...]: ...


class EntityResolver(Protocol):
    async def resolve(
        self,
        document: NewsDocument,
        mentions: tuple[EntityMention, ...],
        candidates: tuple[Entity, ...],
    ) -> AnalysisResult: ...


class EventExtractor(Protocol):
    async def extract(
        self, document: NewsDocument, entities: tuple[Entity, ...]
    ) -> tuple[NewsEvent, ...]: ...


class EmbeddingResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    document_id: DocumentId
    model_name: str
    model_version: str
    values: tuple[float, ...] = Field(min_length=1)


class EmbeddingProvider(Protocol):
    async def embed(self, document: NewsDocument) -> EmbeddingResult: ...
