"""Typed model ports. No models, providers, inference or downloads in this phase."""

from typing import Protocol

from aegis.domain.models import AnalysisResult, Entity, EntityMention, NewsDocument


class SentimentAnalyzer(Protocol):
    async def analyze(self, document: NewsDocument) -> AnalysisResult: ...


class TopicClassifier(Protocol):
    async def classify(self, document: NewsDocument) -> AnalysisResult: ...


class EntityExtractor(Protocol):
    async def extract(self, document: NewsDocument) -> AnalysisResult: ...


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
    ) -> AnalysisResult: ...


class EmbeddingProvider(Protocol):
    async def embed(self, document: NewsDocument) -> AnalysisResult: ...
