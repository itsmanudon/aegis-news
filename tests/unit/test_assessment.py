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
