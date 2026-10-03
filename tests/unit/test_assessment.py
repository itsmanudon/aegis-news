from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.intelligence.assessment import (
    classification_report,
    load_assessment,
    retrieval_report,
    span_report,
)


def test_span_detection_and_entity_typing_are_separate():
    gold = {("doc", 0, 10, "organization")}
    predicted = {("doc", 0, 10, "other"), ("doc", 20, 30, "other")}
    result = span_report(gold, predicted)
    assert result["typed"]["f1"] == 0
    assert result["span_only"]["precision"] == 0.5
    assert result["span_only"]["recall"] == 1


def test_abstentions_remain_in_classification_denominator():
    result = classification_report(["positive", "negative"], ["positive", "unavailable"])
    assert result["accuracy"] == 0.5
    assert result["confusion_matrix"]["negative"]["unavailable"] == 1
    assert result["support"] == 2
    with pytest.raises(ValueError):
        classification_report(["positive"], [])


def test_retrieval_excludes_unjudged_queries_and_counts_missing_results():
    result = retrieval_report({"a": ["b"], "b": []}, {"a": ["c", "b"], "b": ["a"]}, 3)
    assert result["judged_queries"] == 1
    assert result["mrr"] == 0.5
    assert result["recall_at_3"] == 1
    missing = retrieval_report({"a": ["b"]}, {}, 3)
    assert missing["mrr"] == 0
    assert missing["recall_at_3"] == 0


def test_gold_has_diverse_categories_valid_offsets_and_explicit_review_status():
    dataset = load_assessment(Path("ml/datasets/gold/assessment-v1.json"))
    assert len(dataset.cases) >= 16
    assert len({case.category for case in dataset.cases}) >= 8
    assert dataset.license == "CC0-1.0"
    assert "human adjudication pending" in dataset.annotation_status
    assert any(case.media_path for case in dataset.cases)
    assert any(m.entity_id is None for case in dataset.cases for m in case.sample.mentions)


@pytest.mark.asyncio
async def test_retrieval_ties_use_document_ids_not_random_analysis_ids():
    from aegis.intelligence.assessment import assessment_rankings
    from aegis.intelligence.engine import build_engine

    dataset = load_assessment(Path("ml/datasets/gold/assessment-v1.json"))
    embedding = await build_engine("offline").embeddings.embed(dataset.cases[0].sample.document)
    docs = sorted(case.sample.document.document_id for case in dataset.cases)[:3]
    analysis_ids = [f"ana_00000000-0000-0000-0000-{i:012x}" for i in (3, 2, 1)]
    first = {
        doc: embedding.model_copy(update={"analysis_id": analysis, "document_id": doc})
        for doc, analysis in zip(docs, analysis_ids, strict=True)
    }
    second = {
        doc: item.model_copy(update={"analysis_id": "ana_" + doc.removeprefix("doc_")})
        for doc, item in first.items()
    }
    expected = {doc: [candidate for candidate in docs if candidate != doc] for doc in docs}
    assert assessment_rankings(first, datetime.now(UTC)) == expected
    assert assessment_rankings(second, datetime.now(UTC)) == expected


@pytest.mark.asyncio
async def test_invalid_predictions_invalidate_profile_and_keep_denominators(monkeypatch):
    from aegis.intelligence import assessment
    from aegis.intelligence.engine import build_engine
    from aegis.intelligence.errors import InvalidPrediction

    class BrokenTopics:
        async def classify(self, document):
            raise InvalidPrediction("invalid synthetic prediction")

    engine = replace(build_engine("offline"), topics=BrokenTopics())
    monkeypatch.setattr(assessment, "build_engine", lambda _: engine)
    dataset = load_assessment(Path("ml/datasets/gold/assessment-v1.json"))
    report = await assessment.assess(dataset, "offline", 1)
    assert report["execution_status"] == "failed: inference errors"
    assert report["quality_metrics_valid_for_whole_profile"] is False
    assert report["metrics"]["topics"]["support"] == 16
    assert report["metrics"]["topics"]["accuracy"] == 0


def test_failed_assessment_cli_writes_diagnostics_then_exits_nonzero(monkeypatch, tmp_path):
    from aegis.intelligence import assessment

    async def failed(*args):
        return {"execution_status": "failed: inference errors"}

    target = tmp_path / "report.json"
    monkeypatch.setattr(assessment, "assess", failed)
    monkeypatch.setattr("sys.argv", ["assessment", "--output", str(target)])
    with pytest.raises(SystemExit) as exc:
        assessment.main()
    assert exc.value.code == 1
    assert "failed: inference errors" in target.read_text()
