import copy
import json
from pathlib import Path

import pytest

from aegis.intelligence.assessment import load_assessment
from aegis.intelligence.config import profile
from aegis.intelligence.review import validate_review
from scripts.benchmark_profiles import verify_manifest
from scripts.evaluation_device import device_profile


@pytest.fixture
def datasets():
    root = Path("ml/datasets/gold")
    return (
        json.loads((root / "assessment-v3-human.json").read_text()),
        json.loads((root / "assessment-v2.json").read_text()),
    )


def test_completed_review_and_manifest(datasets):
    review, source = datasets
    assert validate_review(review, source) == {
        "reviewed_cases": 16,
        "changed_cases": 0,
        "changes": 0,
    }
    manifest = verify_manifest(Path("ml/datasets/gold/manifest-v3-human.json"))
    data = load_assessment(Path("ml/datasets/gold/assessment-v3-human.json"))
    assert data.annotation_status == "Independent human review completed"
    assert len(data.cases) == manifest["sample_count"] == 16
    assert sum(len(c.sample.mentions) for c in data.cases) == manifest["entity_mentions"] == 17
    assert sum(len(c.expected_events) for c in data.cases) == manifest["event_sentences"] == 12


@pytest.mark.parametrize("mutation", ["pending", "duplicate", "document", "offset", "snapshot"])
def test_rejects_invalid_review(datasets, mutation):
    review, source = datasets
    case = review["cases"][0]
    if mutation == "pending":
        case["adjudication"]["status"] = "pending_review"
    elif mutation == "duplicate":
        review["cases"][1] = copy.deepcopy(case)
    elif mutation == "document":
        case["sample"]["document"]["text"] += " altered"
    elif mutation == "offset":
        case["sample"]["mentions"][0]["extraction"]["end_offset"] += 1
    else:
        case["adjudication"]["original_labels"]["topic"] = "general"
    with pytest.raises(ValueError):
        validate_review(review, source)


def test_rejects_unlogged_label_change(datasets):
    review, source = datasets
    review["cases"][0]["sample"]["sentiment"] = "neutral"
    with pytest.raises(ValueError, match="unlogged"):
        validate_review(review, source)


def test_logged_human_change_is_preserved_without_deciding_quality(datasets):
    review, source = datasets
    case = review["cases"][0]
    case["sample"]["sentiment"] = "neutral"
    case["adjudication"]["changes"] = [
        {"field": "sentiment", "old_value": "positive", "new_value": "neutral", "reason": "Human"}
    ]
    assert validate_review(review, source)["changes"] == 1
    case["adjudication"]["changes"][0]["new_value"] = "negative"
    with pytest.raises(ValueError, match="new value mismatch"):
        validate_review(review, source)


def test_logged_nested_entity_change_matches_actual_annotation(datasets):
    review, source = datasets
    case = review["cases"][0]
    case["sample"]["mentions"][0]["entity_id"] = None
    case["adjudication"]["changes"] = [
        {
            "field": "mentions.0.entity_id",
            "old_value": source["cases"][0]["sample"]["mentions"][0]["entity_id"],
            "new_value": None,
        }
    ]
    assert validate_review(review, source)["changed_cases"] == 1


def test_gpu_device_override_changes_only_device_and_keeps_cpu_default():
    original = profile("light")
    gpu = device_profile("light", "cuda:0")
    for key, spec in original:
        changed = getattr(gpu, key)
        assert changed.model_dump(exclude={"device"}) == spec.model_dump(exclude={"device"})
        assert changed.device == ("cpu" if spec.backend == "baseline" else "cuda:0")
    assert profile("light") == original
    with pytest.raises(ValueError, match="CPU-only"):
        device_profile("offline", "cuda:0")
