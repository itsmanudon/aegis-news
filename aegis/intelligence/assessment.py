"""Small-set assessment: explicit gold, abstention-aware scores, no model downloads."""

import argparse
import asyncio
import hashlib
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, model_validator

from aegis.domain.models import (
    AnalysisResult,
    EntityExtractionResult,
    EntityMention,
    EventExtractionResult,
    NewsEvent,
)
from aegis.intelligence.config import profile
from aegis.intelligence.engine import build_engine
from aegis.intelligence.errors import IntelligenceError
from aegis.intelligence.evaluation import GoldSample, classification_metrics
from aegis.intelligence.extensions import EventClassifier
from aegis.intelligence.models import registry_manifest
from aegis.intelligence.resolution import Resolver
from aegis.intelligence.similarity import similar_analyses
from aegis.intelligence.taxonomy import EVENTS


def set_scores[T](gold: set[T], predicted: set[T]) -> dict[str, float]:
    tp = len(gold & predicted)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def classification_report(gold: Sequence[str], predicted: Sequence[str]) -> dict[str, Any]:
    scores: dict[str, Any] = classification_metrics(gold, predicted)
    labels = sorted(set(gold) | set(predicted))
    scores["support"] = len(gold)
    scores["confusion_matrix"] = {
        actual: {
            guess: sum(g == actual and p == guess for g, p in zip(gold, predicted, strict=True))
            for guess in labels
        }
        for actual in labels
    }
    return scores


def span_report(gold: set[tuple[Any, ...]], predicted: set[tuple[Any, ...]]) -> dict[str, Any]:
    return {
        "typed": set_scores(gold, predicted),
        "span_only": set_scores({s[:3] for s in gold}, {s[:3] for s in predicted}),
        "gold_count": len(gold),
        "predicted_count": len(predicted),
    }


def retrieval_report(
    relevance: dict[str, list[str]], rankings: dict[str, list[str]], k: int
) -> dict[str, Any]:
    if k < 1:
        raise ValueError("positive retrieval cutoff required")
    reciprocal, recall = [], []
    for query, relevant in relevance.items():
        if not relevant:
            continue
        ranked = rankings.get(query, [])
        reciprocal.append(next((1 / (i + 1) for i, d in enumerate(ranked) if d in relevant), 0))
        recall.append(len(set(ranked[:k]) & set(relevant)) / len(set(relevant)))
    return {
        "judged_queries": len(recall),
        "mrr": statistics.mean(reciprocal) if reciprocal else None,
        f"recall_at_{k}": statistics.mean(recall) if recall else None,
    }


class GoldEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_type: str
    evidence_text: str


class AssessmentCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sample: GoldSample
    category: str
    expected_events: tuple[GoldEvent, ...] = ()
    relevant_documents: tuple[str, ...] = ()
    media_path: str | None = None
    annotation_note: str

    @model_validator(mode="after")
    def valid_events(self) -> "AssessmentCase":
        for event in self.expected_events:
            if (
                event.event_type not in EVENTS
                or event.evidence_text not in self.sample.document.text
            ):
                raise ValueError("gold event taxonomy/evidence mismatch")
        return self


class AssessmentSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str
    license: str
    annotation_status: str
    cases: tuple[AssessmentCase, ...]

    @model_validator(mode="after")
    def valid_ids(self) -> "AssessmentSet":
        ids = {c.sample.document.document_id for c in self.cases}
        if not self.cases or len(ids) != len(self.cases):
            raise ValueError("nonempty assessment with unique document IDs required")
        for case in self.cases:
            if any(
                d not in ids or d == case.sample.document.document_id
                for d in case.relevant_documents
            ):
                raise ValueError("relevance must refer to another assessment document")
        return self


def load_assessment(path: Path) -> AssessmentSet:
    return AssessmentSet.model_validate_json(path.read_text(encoding="utf-8"))


def latency_report(samples: Sequence[float]) -> dict[str, float | int]:
    if not samples:
        return {"count": 0}
    ordered = sorted(samples)
    return {
        "count": len(samples),
        "median_ms": statistics.median(samples),
        "p95_ms": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))],
        "total_ms": sum(samples),
    }


def assessment_rankings(
    embeddings: dict[str, AnalysisResult], as_of: datetime
) -> dict[str, list[str]]:
    documents = {value.analysis_id: key for key, value in embeddings.items()}
    return {
        doc_id: [
            documents[analysis_id]
            for analysis_id, _ in sorted(
                similar_analyses(
                    query,
                    tuple(v for k, v in embeddings.items() if k != doc_id),
                    as_of=as_of,
                    limit=len(embeddings),
                ),
                key=lambda item: (-item[1], documents[item[0]]),
            )
        ]
        for doc_id, query in embeddings.items()
    }


async def assess(dataset: AssessmentSet, name: str, rounds: int = 3) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("positive benchmark rounds required")
    engine = build_engine(name)
    latency: dict[str, list[float]] = {}
    failures: list[dict[str, str]] = []
    metadata: dict[str, Any] = {}
    gold_spans: set[tuple[Any, ...]] = set()
    predicted_spans: set[tuple[Any, ...]] = set()
    gold_events: set[tuple[Any, ...]] = set()
    predicted_events: set[tuple[Any, ...]] = set()
    labels: dict[str, list[str]] = {"topics": [], "sentiment": [], "event_classification": []}
    embeddings: dict[str, AnalysisResult] = {}
    predictions: list[dict[str, Any]] = []
    resolution_correct = resolution_top = resolution_count = 0

    async def measured(
        task: str, doc_id: str, call: Callable[[], Awaitable[AnalysisResult]]
    ) -> AnalysisResult | None:
        started = time.perf_counter()
        try:
            return await call()
        except IntelligenceError as exc:
            failures.append({"document_id": doc_id, "task": task, "reason": type(exc).__name__})
            return None
        finally:
            latency.setdefault(task, []).append((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    tracemalloc.start()
    try:
        for iteration in range(rounds):
            for case in dataset.cases:
                sample, document = case.sample, case.sample.document
                doc_id = document.document_id
                mentions = tuple(
                    EntityMention(
                        mention_id="mention_" + str(uuid5(NAMESPACE_URL, f"{doc_id}:{i}")),
                        document_id=doc_id,
                        surface=m.extraction.surface,
                        start_offset=m.extraction.start_offset,
                        end_offset=m.extraction.end_offset,
                        evidence_kind="fact",
                    )
                    for i, m in enumerate(sample.mentions)
                )
                resolver = Resolver(aliases=sample.aliases)
                event = NewsEvent(
                    event_id="evt_" + str(uuid5(NAMESPACE_URL, doc_id)),
                    summary=sample.event_summary or document.text,
                    document_ids=(doc_id,),
                    created_at=document.created_at,
                    available_at=document.created_at,
                    evidence_kind="fact",
                )
                calls: dict[str, Callable[[], Awaitable[AnalysisResult]]] = {
                    "entities": partial(engine.entities.extract, document),
                    "topics": partial(engine.topics.classify, document),
                    "sentiment": partial(engine.sentiment.analyze, document),
                    "embedding": partial(engine.embeddings.embed, document),
                    "resolution": partial(resolver.resolve, document, mentions, sample.candidates),
                    "events": partial(engine.events.extract, document, ()),
                }
                if isinstance(engine.events, EventClassifier):
                    calls["event_classification"] = partial(engine.events.classify, document, event)
                results = {task: await measured(task, doc_id, call) for task, call in calls.items()}
                if iteration:
                    continue
                for task, result in results.items():
                    if result is not None:
                        metadata[task] = result.model_dump(
                            mode="json",
                            exclude={
                                "outputs",
                                "analysis_id",
                                "document_id",
                                "created_at",
                                "available_at",
                            },
                        )
                predicted = {
                    task: result.model_dump(mode="json")["outputs"] if result else []
                    for task, result in results.items()
                }
                predictions.append({"document_id": doc_id, "outputs": predicted})
                for task in labels:
                    labels[task].append(
                        str(predicted[task][0]["label"]) if predicted.get(task) else "unavailable"
                    )
                gold_spans.update(
                    (
                        doc_id,
                        m.extraction.start_offset,
                        m.extraction.end_offset,
                        m.extraction.predicted_kind,
                    )
                    for m in sample.mentions
                )
                ner = results["entities"]
                if ner:
                    predicted_spans.update(
                        (doc_id, o.start_offset, o.end_offset, o.predicted_kind)
                        for o in ner.outputs
                        if isinstance(o, EntityExtractionResult)
                    )
                gold_events.update(
                    (doc_id, e.event_type, e.evidence_text) for e in case.expected_events
                )
                extracted = results["events"]
                if extracted:
                    predicted_events.update(
                        (doc_id, o.proposed_event_type, o.evidence_text)
                        for o in extracted.outputs
                        if isinstance(o, EventExtractionResult)
                    )
                for i, mention in enumerate(sample.mentions):
                    outputs = predicted["resolution"]
                    resolution_correct += (
                        bool(outputs) and outputs[i]["entity_id"] == mention.entity_id
                    )
                    if mention.entity_id is not None:
                        resolution_top += mention.entity_id in {
                            e
                            for e, _ in resolver.rank(
                                mention.extraction.surface, sample.candidates
                            )[:3]
                        }
                    elif outputs:
                        resolution_top += outputs[i]["entity_id"] is None
                    resolution_count += 1
                embedding = results["embedding"]
                if embedding is not None:
                    embeddings[doc_id] = embedding
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    elapsed = time.perf_counter() - started
    rankings = assessment_rankings(embeddings, datetime.now(UTC))
    metrics = {
        "ner": span_report(gold_spans, predicted_spans),
        "topics": classification_report([c.sample.topic for c in dataset.cases], labels["topics"]),
        "sentiment": classification_report(
            [c.sample.sentiment for c in dataset.cases], labels["sentiment"]
        ),
        "event_classification": classification_report(
            [c.sample.event for c in dataset.cases], labels["event_classification"]
        ),
        "event_extraction": {
            **set_scores(gold_events, predicted_events),
            "gold_count": len(gold_events),
            "predicted_count": len(predicted_events),
        },
        "resolution": {
            "gold_mentions": resolution_count,
            "accuracy": resolution_correct / resolution_count if resolution_count else None,
            "top_3_accuracy_including_correct_abstentions": resolution_top / resolution_count
            if resolution_count
            else None,
            "protocol": "gold mentions and supplied candidates; independent of NER",
        },
        "retrieval": retrieval_report(
            {c.sample.document.document_id: list(c.relevant_documents) for c in dataset.cases},
            rankings,
            3,
        ),
    }
    unexpected_errors = any(
        f["reason"] not in {"NoPredictions", "ModelUnavailable"} for f in failures
    )
    unavailable = any(f["reason"] == "ModelUnavailable" for f in failures)
    return {
        "profile": name,
        "execution_status": "failed: inference errors"
        if unexpected_errors
        else "partial: optional models unavailable"
        if unavailable
        else "completed",
        "quality_metrics_valid_for_whole_profile": not (unexpected_errors or unavailable),
        "samples": len(dataset.cases),
        "rounds": rounds,
        "dataset_sha256": hashlib.sha256(dataset.model_dump_json().encode()).hexdigest(),
        "annotation_status": dataset.annotation_status,
        "scope": "Tiny synthetic development set; not a held-out real-news quality estimate",
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "architecture": platform.machine(),
            "gpu": "not used",
            "download_bytes": 0,
        },
        "registry": registry_manifest(profile(name)),
        "producing_models": metadata,
        "metrics": metrics,
        "predictions": predictions,
        "nearest_neighbors": {k: v[:3] for k, v in rankings.items()},
        "failures": failures,
        "timing": {k: latency_report(v) for k, v in latency.items()},
        "benchmark": {
            "elapsed_seconds": elapsed,
            "documents_per_second": rounds * len(dataset.cases) / elapsed,
            "python_tracemalloc_peak_bytes": peak,
            "memory_limitation": "Python allocations only; excludes native/GPU/process RSS",
            "warmup": "none; first and warm iterations included",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/gold/assessment-v1.json"))
    parser.add_argument("--profile", choices=("offline", "light", "full"), default="offline")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(assess(load_assessment(args.dataset), args.profile, args.rounds))
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    if report["execution_status"] == "failed: inference errors":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
