from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from aegis.domain.ids import new_id


async def test_append_adapter_roundtrips_frozen_analysis(document):
    from aegis.intelligence.engine import build_engine
    from aegis.intelligence.persistence import append_analysis, from_row

    result = await build_engine("offline").embeddings.embed(document)
    with Session() as session:
        row = append_analysis(session, result)
        assert row in session.new
        assert from_row(row) == result
        assert row.outputs[0]["result_type"] == "embedding"
        assert row.analysis_id == result.analysis_id


async def test_similarity_rejects_incompatible_space_and_future(document):
    from aegis.intelligence.engine import build_engine
    from aegis.intelligence.similarity import similar_analyses

    ai = build_engine("offline")
    query = await ai.embeddings.embed(document)
    same = await ai.embeddings.embed(document.model_copy(update={"document_id": new_id("doc")}))
    other = same.model_copy(update={"model_version": "different"})
    future = same.model_copy(update={"available_at": same.available_at + timedelta(days=1)})
    found = similar_analyses(query, (same, other, future), as_of=same.available_at, limit=3)
    assert len(found) == 1
    assert found[0][0] == same.analysis_id
    assert found[0][1] == pytest.approx(1.0)


def test_metrics_are_hand_computed():
    from aegis.intelligence.evaluation import classification_metrics, span_metrics

    metrics = classification_metrics(["a", "a", "b"], ["a", "b", "b"])
    assert metrics["accuracy"] == pytest.approx(2 / 3)
    assert metrics["macro_f1"] == pytest.approx(2 / 3)
    spans = span_metrics(
        {("doc1", 0, 4, "organization"), ("doc1", 8, 10, "person")},
        {("doc1", 0, 4, "organization"), ("doc1", 12, 16, "location")},
    )
    assert spans == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    with pytest.raises(ValueError):
        classification_metrics(["a"], [])


async def test_gold_evaluation_runs_and_records_provenance():
    from pathlib import Path

    from aegis.intelligence.engine import build_engine
    from aegis.intelligence.evaluation import evaluate, load_gold

    records = load_gold(Path("ml/datasets/gold/synthetic.jsonl"))
    report = await evaluate(build_engine("offline"), records)
    assert report["samples"] >= 4
    assert report["dataset_sha256"]
    assert set(report["metrics"]) == {"ner", "topic", "sentiment", "resolution", "event"}
    assert report["analyses"]
    assert all("configuration_hash" in a for a in report["analyses"])
    assert report["resource_warning"]


async def test_activity_no_predictions_is_non_retryable(document):
    from temporalio.exceptions import ApplicationError

    from aegis.intelligence.engine import build_engine
    from apps.worker.ai_activities import AIActivities

    with pytest.raises(ApplicationError) as failure:
        await AIActivities(build_engine("offline")).analyze_entities(
            document.model_copy(update={"text": "nothing found"})
        )
    assert failure.value.non_retryable
    assert failure.value.type == "NoPredictions"


async def test_temporal_pydantic_payload_roundtrip(document):
    from temporalio.contrib.pydantic import pydantic_data_converter

    from aegis.domain.models import AnalysisResult
    from aegis.intelligence.engine import build_engine
    from apps.worker.ai_activities import ResolutionRequest

    request = ResolutionRequest(document=document)
    result = await build_engine("offline").topics.classify(document)
    payloads = await pydantic_data_converter.encode([request, result])
    decoded = await pydantic_data_converter.decode(payloads, [ResolutionRequest, AnalysisResult])
    assert decoded == [request, result]


def test_long_gold_documents_require_explicit_event_summary(document):
    from pydantic import ValidationError

    from aegis.intelligence.evaluation import GoldSample

    long = document.model_copy(update={"text": "ordinary text " * 100})
    with pytest.raises(ValidationError):
        GoldSample(document=long, topic="general", sentiment="neutral", event="general")
    sample = GoldSample(
        document=long,
        topic="general",
        sentiment="neutral",
        event="general",
        event_summary="Ordinary notice",
    )
    assert sample.event_summary == "Ordinary notice"
