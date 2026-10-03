import hashlib
import json
from pathlib import Path

from aegis.intelligence.assessment import latency_report, load_assessment


def test_reviewed_dataset_preserves_original_text_spans_and_declares_agent_review():
    root = Path("ml/datasets/gold")
    original = load_assessment(root / "assessment-v1.json")
    reviewed = load_assessment(root / "assessment-v2.json")
    assert reviewed.version == "gold_v2"
    assert "human sign-off pending" in reviewed.annotation_status
    assert len(reviewed.cases) == len(original.cases) == 16
    for before, after in zip(original.cases, reviewed.cases, strict=True):
        assert before.sample.document == after.sample.document
        assert before.sample.mentions == after.sample.mentions
        assert before.sample.candidates == after.sample.candidates
        assert before.relevant_documents == after.relevant_documents
    record = json.loads((root / "adjudication-v2.json").read_text())
    assert len(record["records"]) == 16
    assert sum(row["changed"] for row in record["records"]) == 2
    assert all(row["reason"] and row["ambiguity_notes"] for row in record["records"])
    assert reviewed.cases[14].sample.event == "general"
    assert not reviewed.cases[14].expected_events


def test_review_manifest_hashes_and_counts_are_exact():
    manifest = json.loads(Path("ml/datasets/gold/manifest-v2.json").read_text())
    for filename, entry in manifest["files"].items():
        content = Path(filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert len(content) == entry["bytes"]
    dataset = load_assessment(Path("ml/datasets/gold/assessment-v2.json"))
    assert len(dataset.cases) == manifest["sample_count"]
    assert sum(len(c.sample.mentions) for c in dataset.cases) == manifest["entity_mentions"]
    assert sum(len(c.expected_events) for c in dataset.cases) == manifest["event_sentences"]


def test_latency_p95_uses_nearest_rank_at_exact_percentile_boundary():
    assert latency_report(list(range(1, 21)))["p95_ms"] == 19
    assert latency_report(list(range(1, 81)))["p95_ms"] == 76
    assert latency_report([1, 2, 3, 4, 5])["p95_ms"] == 5
