"""Register bound activities on a future worker; no ingestion workflow ownership."""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict
from temporalio import activity
from temporalio.exceptions import ApplicationError

from aegis.domain.models import AnalysisResult, Entity, EntityMention, NewsDocument, NewsEvent
from aegis.intelligence.engine import IntelligenceEngine
from aegis.intelligence.errors import InvalidPrediction, NoPredictions, UnsupportedLanguage
from aegis.intelligence.extensions import EventClassifier


class ResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document: NewsDocument
    mentions: tuple[EntityMention, ...] = ()
    candidates: tuple[Entity, ...] = ()


class EventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document: NewsDocument
    entities: tuple[Entity, ...] = ()


class EventClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document: NewsDocument
    event: NewsEvent


class AIActivities:
    def __init__(self, engine: IntelligenceEngine) -> None:
        self.engine = engine

    async def _run(self, task: Awaitable[AnalysisResult]) -> AnalysisResult:
        try:
            return await task
        except (NoPredictions, UnsupportedLanguage, InvalidPrediction) as exc:
            raise ApplicationError(
                "AI task has a permanent outcome", type=type(exc).__name__, non_retryable=True
            ) from exc

    @activity.defn(name="analyze_entities")
    async def analyze_entities(self, document: NewsDocument) -> AnalysisResult:
        return await self._run(self.engine.entities.extract(document))

    @activity.defn(name="analyze_topics")
    async def analyze_topics(self, document: NewsDocument) -> AnalysisResult:
        return await self._run(self.engine.topics.classify(document))

    @activity.defn(name="analyze_sentiment")
    async def analyze_sentiment(self, document: NewsDocument) -> AnalysisResult:
        return await self._run(self.engine.sentiment.analyze(document))

    @activity.defn(name="generate_embedding")
    async def generate_embedding(self, document: NewsDocument) -> AnalysisResult:
        return await self._run(self.engine.embeddings.embed(document))

    @activity.defn(name="resolve_entities")
    async def resolve_entities(self, request: ResolutionRequest) -> AnalysisResult:
        return await self._run(
            self.engine.resolver.resolve(request.document, request.mentions, request.candidates)
        )

    @activity.defn(name="extract_events")
    async def extract_events(self, request: EventRequest) -> AnalysisResult:
        return await self._run(self.engine.events.extract(request.document, request.entities))

    @activity.defn(name="classify_event")
    async def classify_event(self, request: EventClassificationRequest) -> AnalysisResult:
        if not isinstance(self.engine.events, EventClassifier):
            raise TypeError("configured event provider does not expose classification")
        return await self._run(self.engine.events.classify(request.document, request.event))

    def registered(self) -> list[Callable[..., Any]]:
        return [
            self.analyze_entities,
            self.analyze_topics,
            self.analyze_sentiment,
            self.generate_embedding,
            self.resolve_entities,
            self.extract_events,
            self.classify_event,
        ]
