"""Compose independent providers; callers may replace any frozen-port implementation."""

from dataclasses import dataclass

from aegis.intelligence.config import Profile, profile
from aegis.intelligence.interfaces import (
    EmbeddingProvider,
    EntityExtractor,
    EntityResolver,
    EventExtractor,
    SentimentAnalyzer,
    TopicClassifier,
)
from aegis.intelligence.local_runtime import LocalRuntime
from aegis.intelligence.providers import Embeddings, Entities, Events, Sentiment, Topics
from aegis.intelligence.resolution import Resolver
from aegis.intelligence.runtime import BaselineRuntime, Runtime


@dataclass(frozen=True)
class IntelligenceEngine:
    entities: EntityExtractor
    topics: TopicClassifier
    sentiment: SentimentAnalyzer
    embeddings: EmbeddingProvider
    resolver: EntityResolver
    events: EventExtractor


def build_engine(
    resource_profile: str | Profile = "light", runtime: Runtime | None = None
) -> IntelligenceEngine:
    specs = profile(resource_profile) if isinstance(resource_profile, str) else resource_profile
    local = runtime or LocalRuntime()
    baseline = BaselineRuntime()

    def backend(name: str) -> Runtime:
        return runtime or (baseline if name == "baseline" else local)

    return IntelligenceEngine(
        entities=Entities(specs.ner, backend(specs.ner.backend)),
        topics=Topics(specs.topic, backend(specs.topic.backend)),
        sentiment=Sentiment(specs.sentiment, backend(specs.sentiment.backend)),
        embeddings=Embeddings(specs.embedding, backend(specs.embedding.backend)),
        resolver=Resolver(),
        events=Events(specs.event, backend(specs.event.backend)),
    )
