"""Task-specific adapters implementing the frozen intelligence ports."""

import asyncio
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import TypeAdapter, ValidationError

from aegis.domain.models import (
    AnalysisResult,
    Confidence,
    EmbeddingResult,
    Entity,
    EntityExtractionResult,
    EntityMention,
    EventClassificationResult,
    EventExtractionResult,
    NewsDocument,
    NewsEvent,
    SentimentResult,
    TopicResult,
)
from aegis.intelligence.common import envelope, validate_document
from aegis.intelligence.config import ModelSpec
from aegis.intelligence.errors import IntelligenceError, InvalidPrediction
from aegis.intelligence.runtime import Prediction, Runtime
from aegis.intelligence.taxonomy import EVENTS, TOPICS


class TaskProvider:
    def __init__(self, spec: ModelSpec, runtime: Runtime) -> None:
        self.spec = ModelSpec.model_validate(spec.model_dump())
        self.runtime = runtime

    async def predict(
        self,
        document: NewsDocument,
        task: str,
        text: str | None = None,
        labels: tuple[str, ...] = (),
    ) -> Sequence[Prediction]:
        validate_document(document)
        try:
            predictions = await asyncio.to_thread(
                self.runtime.predict,
                task,
                document.text if text is None else text,
                self.spec,
                labels,
            )
            if task != "embedding":
                try:
                    for prediction in predictions:
                        TypeAdapter(Confidence).validate_python(prediction["score"])
                except (KeyError, TypeError, ValidationError) as exc:
                    raise InvalidPrediction("invalid prediction confidence") from exc
            return predictions
        except IntelligenceError:
            raise
        except Exception as exc:
            raise IntelligenceError(f"{task} inference failed") from exc


class Entities(TaskProvider):
    async def extract(self, document: NewsDocument) -> AnalysisResult:
        started = datetime.now(UTC)
        predictions = await self.predict(document, "entity_extraction")
        try:
            outputs = tuple(
                EntityExtractionResult(
                    surface=p["surface"],
                    start_offset=p["start"],
                    end_offset=p["end"],
                    predicted_kind=p["kind"],
                    confidence=p["score"],
                )
                for p in predictions
            )
            for output in outputs:
                if document.text[output.start_offset : output.end_offset] != output.surface:
                    raise InvalidPrediction("NER span does not match document text")
            outputs = tuple(o for o in outputs if o.confidence >= self.spec.threshold)
        except (KeyError, TypeError, ValidationError) as exc:
            raise InvalidPrediction("invalid entity prediction") from exc
        return envelope(document, self.spec, outputs, started, self.runtime.metadata)


class Topics(TaskProvider):
    async def classify(self, document: NewsDocument) -> AnalysisResult:
        started = datetime.now(UTC)
        predictions = await self.predict(document, "topic", labels=tuple(TOPICS))
        try:
            outputs = tuple(
                TopicResult(label=p["label"], confidence=p["score"]) for p in predictions[:1]
            )
            if any(o.label not in TOPICS for o in outputs):
                raise InvalidPrediction("unknown topic label")
        except (KeyError, TypeError, ValidationError) as exc:
            raise InvalidPrediction("invalid topic prediction") from exc
        return envelope(document, self.spec, outputs, started, self.runtime.metadata)


class Sentiment(TaskProvider):
    async def _analyze(
        self, document: NewsDocument, text: str, entity_id: str | None = None
    ) -> AnalysisResult:
        started = datetime.now(UTC)
        predictions = await self.predict(document, "sentiment", text)
        try:
            if not predictions:
                outputs: tuple[SentimentResult, ...] = ()
            else:
                top = max(predictions, key=lambda p: p["score"])
                scores = {p["label"]: float(p["score"]) for p in predictions}
                score = scores.get("positive", 0) - scores.get("negative", 0)
                outputs = (
                    SentimentResult(
                        label=top["label"],
                        score=score,
                        confidence=top["score"],
                        entity_id=entity_id,
                    ),
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidPrediction("invalid sentiment prediction") from exc
        return envelope(
            document,
            self.spec,
            outputs,
            started,
            self.runtime.metadata,
            context={"entity_id": entity_id, "context_text": text},
        )

    async def analyze(self, document: NewsDocument) -> AnalysisResult:
        return await self._analyze(document, document.text)

    async def analyze_entity(
        self, document: NewsDocument, entity: Entity, mentions: tuple[EntityMention, ...]
    ) -> AnalysisResult:
        """Sentence-window proxy, not an aspect-trained sentiment model."""
        Entity.model_validate(entity.model_dump())
        for mention in mentions:
            EntityMention.model_validate(mention.model_dump())
            if mention.document_id != document.document_id:
                raise ValueError("mention belongs to another document")
            if document.text[mention.start_offset : mention.end_offset] != mention.surface:
                raise ValueError("mention span does not match document")
        sentences = []
        for match in re.finditer(r"[^.!?]+[.!?]?", document.text):
            if any(
                m.entity_id == entity.entity_id and match.start() <= m.start_offset < match.end()
                for m in mentions
            ):
                sentences.append(match.group())
        if not sentences:
            from aegis.intelligence.errors import NoPredictions

            raise NoPredictions("no sentence evidence for requested entity")
        return await self._analyze(document, " ".join(sentences), entity.entity_id)


class Embeddings(TaskProvider):
    async def embed(self, document: NewsDocument) -> AnalysisResult:
        started = datetime.now(UTC)
        predictions = await self.predict(document, "embedding")
        try:
            if len(predictions) != 1:
                raise InvalidPrediction("embedding inference must return exactly one vector")
            output = EmbeddingResult(values=tuple(predictions[0]["values"]))
            if len(output.values) != self.spec.dimensions:
                raise InvalidPrediction("embedding dimensions do not match configuration")
        except (KeyError, TypeError, ValidationError) as exc:
            raise InvalidPrediction("invalid embedding prediction") from exc
        return envelope(document, self.spec, (output,), started, self.runtime.metadata)


class Events(TaskProvider):
    async def extract(self, document: NewsDocument, entities: tuple[Entity, ...]) -> AnalysisResult:
        started = datetime.now(UTC)
        outputs = []
        for match in re.finditer(r"[^.!?]+[.!?]?", document.text):
            evidence = match.group().strip()
            if not evidence:
                continue
            predictions = await self.predict(document, "event_extraction", evidence, tuple(EVENTS))
            try:
                for p in predictions:
                    if p["label"] not in EVENTS:
                        raise InvalidPrediction("unknown event label")
                    if p["label"] != "general" and p["score"] >= self.spec.threshold:
                        outputs.append(
                            EventExtractionResult(
                                proposed_event_type=p["label"],
                                confidence=p["score"],
                                document_id=document.document_id,
                                evidence_text=evidence,
                            )
                        )
            except (KeyError, TypeError, ValidationError) as exc:
                raise InvalidPrediction("invalid event prediction") from exc
        validate_document(document)
        return envelope(
            document,
            self.spec,
            tuple(outputs),
            started,
            self.runtime.metadata,
            context={"entities": [e.model_dump(mode="json") for e in entities]},
        )

    async def classify(self, document: NewsDocument, event: NewsEvent) -> AnalysisResult:
        NewsEvent.model_validate(event.model_dump())
        if document.document_id not in event.document_ids:
            raise ValueError("classification document must be linked to event revision")
        started = datetime.now(UTC)
        predictions = await self.predict(
            document, "event_classification", event.summary, tuple(EVENTS)
        )
        try:
            outputs = tuple(
                EventClassificationResult(
                    event_id=event.event_id,
                    event_revision=event.revision,
                    label=p["label"],
                    confidence=p["score"],
                )
                for p in predictions[:1]
            )
            if any(o.label not in EVENTS for o in outputs):
                raise InvalidPrediction("unknown event label")
        except (KeyError, TypeError, ValidationError) as exc:
            raise InvalidPrediction("invalid event classification") from exc
        return envelope(
            document,
            self.spec,
            outputs,
            started,
            self.runtime.metadata,
            context={"event": event.model_dump(mode="json")},
        )
