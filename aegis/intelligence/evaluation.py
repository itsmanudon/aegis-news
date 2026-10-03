"""Reproducible evaluation with explicit gold labels; no model downloads by default."""

import argparse
import asyncio
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aegis.domain.models import (
    AnalysisResult,
    Entity,
    EntityExtractionResult,
    EntityMention,
    NewsDocument,
    NewsEvent,
)
from aegis.intelligence.engine import IntelligenceEngine, build_engine
from aegis.intelligence.errors import NoPredictions
from aegis.intelligence.extensions import EventClassifier
from aegis.intelligence.resolution import Resolver
from aegis.intelligence.taxonomy import EVENTS, TOPICS

Span = tuple[str, int, int, str | None]


def span_metrics(gold: set[Span], predicted: set[Span]) -> dict[str, float]:
    true_positive = len(gold & predicted)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def classification_metrics(gold: Sequence[str], predicted: Sequence[str]) -> dict[str, float]:
    if not gold or len(gold) != len(predicted):
        raise ValueError("nonempty, aligned classification labels required")
    f1_scores = []
    for label in sorted(set(gold) | set(predicted)):
        tp = sum(g == p == label for g, p in zip(gold, predicted, strict=True))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted, strict=True))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted, strict=True))
        f1_scores.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0)
    accuracy = sum(g == p for g, p in zip(gold, predicted, strict=True)) / len(gold)
    return {"accuracy": accuracy, "micro_f1": accuracy, "macro_f1": sum(f1_scores) / len(f1_scores)}


class GoldMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    extraction: EntityExtractionResult
    entity_id: str | None = None


class GoldSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document: NewsDocument
    mentions: tuple[GoldMention, ...] = ()
    candidates: tuple[Entity, ...] = ()
    topic: str
    sentiment: str
    event: str
    event_summary: str | None = Field(default=None, min_length=1, max_length=512)
    aliases: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_labels(self) -> "GoldSample":
        if len(self.document.text) > 512 and self.event_summary is None:
            raise ValueError("long gold documents require an explicit event_summary")
        if self.topic not in TOPICS or self.event not in EVENTS:
            raise ValueError("unknown gold taxonomy label")
        if self.sentiment not in ("positive", "negative", "neutral", "mixed"):
            raise ValueError("unknown gold sentiment")
        for mention in self.mentions:
            span = mention.extraction
            if self.document.text[span.start_offset : span.end_offset] != span.surface:
                raise ValueError("gold span does not match document")
            if mention.entity_id and mention.entity_id not in {
                c.entity_id for c in self.candidates
            }:
                raise ValueError("gold resolved entity must be in supplied candidates")
        return self


def load_gold(path: Path) -> tuple[GoldSample, ...]:
    records = tuple(
        GoldSample.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if not records or len({r.document.document_id for r in records}) != len(records):
        raise ValueError("gold dataset must be nonempty with unique document IDs")
    return records


async def evaluate(
    engine: IntelligenceEngine, records: tuple[GoldSample, ...], top_k: int = 3
) -> dict[str, Any]:
    if not records or top_k < 1:
        raise ValueError("nonempty dataset and positive top_k required")
    gold_spans: set[Span] = set()
    predicted_spans: set[Span] = set()
    topics: list[str] = []
    sentiments: list[str] = []
    events: list[str] = []
    analyses: list[dict[str, Any]] = []
    no_predictions: list[dict[str, str]] = []
    resolution_correct, resolution_top_k, mention_count = 0, 0, 0

    def record(result: AnalysisResult, document: NewsDocument) -> None:
        analyses.append(
            {
                **result.model_dump(mode="json", exclude={"outputs"}),
                "document_revision": document.revision,
                "text_sha256": hashlib.sha256(document.text.encode()).hexdigest(),
            }
        )

    for sample in records:
        document = sample.document
        gold_spans.update(
            (
                document.document_id,
                m.extraction.start_offset,
                m.extraction.end_offset,
                m.extraction.predicted_kind,
            )
            for m in sample.mentions
        )
        try:
            ner = await engine.entities.extract(document)
            record(ner, document)
            for output in ner.outputs:
                if isinstance(output, EntityExtractionResult):
                    predicted_spans.add(
                        (
                            document.document_id,
                            output.start_offset,
                            output.end_offset,
                            output.predicted_kind,
                        )
                    )
        except NoPredictions:
            no_predictions.append({"document_id": document.document_id, "task": "ner"})
        topic = await engine.topics.classify(document)
        sentiment = await engine.sentiment.analyze(document)
        topics.append(str(topic.outputs[0].model_dump()["label"]))
        sentiments.append(str(sentiment.outputs[0].model_dump()["label"]))
        record(topic, document)
        record(sentiment, document)
        mentions = tuple(
            EntityMention(
                mention_id="mention_"
                + str(uuid5(NAMESPACE_URL, f"{document.document_id}:gold:{index}")),
                document_id=document.document_id,
                surface=m.extraction.surface,
                start_offset=m.extraction.start_offset,
                end_offset=m.extraction.end_offset,
                evidence_kind="fact",
            )
            for index, m in enumerate(sample.mentions)
        )
        if not isinstance(engine.resolver, Resolver):
            raise TypeError("top-k evaluation requires a candidate-ranking Resolver")
        resolver = Resolver(
            aliases=sample.aliases,
            identifiers=dict(engine.resolver.identifiers),
            threshold=engine.resolver.threshold,
            ambiguity_margin=engine.resolver.ambiguity_margin,
        )
        if mentions:
            result = await resolver.resolve(document, mentions, sample.candidates)
            record(result, document)
            for mention, gold, predicted in zip(
                mentions, sample.mentions, result.outputs, strict=True
            ):
                resolved = predicted.model_dump()["entity_id"]
                resolution_correct += resolved == gold.entity_id
                ranks = resolver.rank(mention.surface, sample.candidates)
                resolution_top_k += (
                    resolved is None
                    if gold.entity_id is None
                    else gold.entity_id in {entity_id for entity_id, _ in ranks[:top_k]}
                )
                mention_count += 1
        if not isinstance(engine.events, EventClassifier):
            raise TypeError("event evaluation requires an EventClassifier")
        # Synthetic/manual gold event is evaluation evidence, never persisted as a canonical fact.
        event = NewsEvent(
            event_id=f"evt_{uuid5(NAMESPACE_URL, document.document_id)}",
            summary=sample.event_summary or document.text,
            document_ids=(document.document_id,),
            created_at=document.created_at,
            available_at=document.created_at,
            evidence_kind="fact",
        )
        classification = await engine.events.classify(document, event)
        record(classification, document)
        events.append(str(classification.outputs[0].model_dump()["label"]))
    return {
        "samples": len(records),
        "dataset_sha256": hashlib.sha256(
            json.dumps([r.model_dump(mode="json") for r in records], sort_keys=True).encode()
        ).hexdigest(),
        "resource_warning": (
            "Small synthetic smoke dataset; scores do not estimate real-news quality."
        ),
        "metrics": {
            "ner": span_metrics(gold_spans, predicted_spans),
            "topic": classification_metrics([r.topic for r in records], topics),
            "sentiment": classification_metrics([r.sentiment for r in records], sentiments),
            "event": classification_metrics([r.event for r in records], events),
            "resolution": {
                "mentions": mention_count,
                "accuracy": resolution_correct / mention_count if mention_count else None,
                f"top_{top_k}_accuracy": resolution_top_k / mention_count
                if mention_count
                else None,
            },
        },
        "analyses": analyses,
        "no_predictions": no_predictions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/gold/synthetic.jsonl"))
    parser.add_argument("--profile", choices=("offline", "light", "full"), default="offline")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(evaluate(build_engine(args.profile), load_gold(args.dataset)))
    report["profile"] = args.profile
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
