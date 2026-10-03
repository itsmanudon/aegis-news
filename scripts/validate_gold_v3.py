"""Check human review and optionally create an exact-byte evidence manifest."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis.intelligence.assessment import load_assessment
from aegis.intelligence.review import validate_review
from scripts.benchmark_profiles import verify_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    root = Path("ml/datasets/gold")
    dataset_path = root / "assessment-v3-human.json"
    review = json.loads(dataset_path.read_text(encoding="utf-8"))
    source = json.loads((root / "assessment-v2.json").read_text(encoding="utf-8"))
    summary = validate_review(review, source)
    dataset = load_assessment(dataset_path)
    verify_manifest(root / "manifest-v2.json")
    if review["annotation_status"] != "Independent human review completed":
        raise ValueError("top-level review status not completed")
    manifest_path = root / "manifest-v3-human.json"
    if args.write_manifest:
        paths = [
            dataset_path,
            root / "assessment-v2.json",
            root / "adjudication-v2.json",
            root / "ADJUDICATION-v2.md",
            root / "manifest-v2.json",
            Path("data/samples/demo-image.png"),
        ]
        manifest: dict[str, Any] = {
            "dataset_version": dataset.version,
            "source_version": "gold_v2",
            "review_status": review["annotation_status"],
            "reviewer_count": 1,
            "reviewer_method": (
                "Independent human review recorded by the user for all 16 cases; agent validates "
                "structure only. No model/threshold/rule tuning."
            ),
            "generated_at": datetime.now(UTC).isoformat(),
            "license": dataset.license,
            "sample_count": len(dataset.cases),
            "entity_mentions": sum(len(c.sample.mentions) for c in dataset.cases),
            "event_sentences": sum(len(c.expected_events) for c in dataset.cases),
            "media_samples": sum(c.media_path is not None for c in dataset.cases),
            **summary,
            "files": {
                p.as_posix(): {
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "bytes": p.stat().st_size,
                }
                for p in paths
            },
            "known_limitations": [
                "One human reviewer; no inter-reviewer agreement estimate",
                "16 short synthetic CC0 English samples, organization-heavy NER",
                "No large real-world held-out corpus or longitudinal drift study",
                "Incomplete coarse retrieval relevance and tiny supplied candidate sets",
            ],
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    verify_manifest(manifest_path)
    print(json.dumps({"result": "passed", **summary}))


if __name__ == "__main__":
    main()
