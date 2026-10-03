"""Structural human-review checks only: never decide whether a gold label is correct."""

from typing import Any

from aegis.intelligence.evaluation import GoldSample


def entity_snapshot(sample: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "surface": m["extraction"]["surface"],
            "kind": m["extraction"]["predicted_kind"],
            "start_offset": m["extraction"]["start_offset"],
            "end_offset": m["extraction"]["end_offset"],
            "entity_id": m["entity_id"],
        }
        for m in sample["mentions"]
    ]


def field_value(case: dict[str, Any], field: str) -> Any:
    if field == "entities":
        return entity_snapshot(case["sample"])
    parts = field.split(".")
    value: Any = case if parts[0] in case else case["sample"]
    for part in parts:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def differing_paths(before: Any, after: Any, prefix: str = "") -> set[str]:
    if before == after:
        return set()
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return set().union(
            *(differing_paths(before[k], after[k], f"{prefix}.{k}".strip(".")) for k in before)
        )
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return set().union(
            *(
                differing_paths(a, b, f"{prefix}.{i}")
                for i, (a, b) in enumerate(zip(before, after, strict=True))
            )
        )
    return {prefix}


def validate_review(review: dict[str, Any], source: dict[str, Any]) -> dict[str, int]:
    if review["version"] != "gold_v3_human" or review["source_version"] != "gold_v2":
        raise ValueError("unexpected reviewed dataset/source version")
    if review["license"] != source["license"]:
        raise ValueError("dataset license changed")
    if review["annotation_status"] != "Independent human review completed":
        raise ValueError("top-level human review status not completed")
    cases = review["cases"]
    originals = {c["sample"]["document"]["document_id"]: c for c in source["cases"]}
    ids = [c["sample"]["document"]["document_id"] for c in cases]
    if len(cases) != 16 or len(set(ids)) != 16 or set(ids) != set(originals):
        raise ValueError("exactly 16 original unique document IDs required")
    change_count = changed_cases = 0
    for case in cases:
        original = originals[case["sample"]["document"]["document_id"]]
        if case["sample"]["document"] != original["sample"]["document"]:
            raise ValueError("original document changed")
        GoldSample.model_validate(case["sample"])  # taxonomy, offsets, candidate references
        block = case["adjudication"]
        if block["status"] != "reviewed":
            raise ValueError(f"human review incomplete: {case['sample']['document']['title']}")
        labels = block["original_labels"]
        for field in ("topic", "sentiment", "event", "entities"):
            if labels[field] != field_value(original, field):
                raise ValueError(f"original label snapshot mismatch: {field}")
        if not isinstance(block["notes"], str) or not isinstance(block["changes"], list):
            raise ValueError("review notes/changes malformed")
        covered = set()
        for change in block["changes"]:
            if (
                not isinstance(change, dict)
                or not {"field", "old_value", "new_value"} <= change.keys()
            ):
                raise ValueError("change requires field, old_value and new_value")
            field = change["field"]
            if not isinstance(field, str) or not field:
                raise ValueError("change field must be a nonempty path")
            if "reason" in change and not isinstance(change["reason"], str):
                raise ValueError("change reason must be text when supplied")
            if change["old_value"] != field_value(original, field):
                raise ValueError(f"change old value mismatch: {field}")
            if change["new_value"] != field_value(case, field):
                raise ValueError(f"change new value mismatch: {field}")
            path = "sample.mentions" if field == "entities" else field
            if path.split(".")[0] not in original:
                path = "sample." + path
            if path in covered:
                raise ValueError(f"duplicate change field: {field}")
            covered.add(path)
        original_fields = {k: v for k, v in original.items() if k != "annotation_note"}
        actual_fields = {
            k: v for k, v in case.items() if k not in {"adjudication", "annotation_note"}
        }
        for difference in differing_paths(original_fields, actual_fields):
            if not any(difference == p or difference.startswith(p + ".") for p in covered):
                raise ValueError(f"unlogged label/data change: {difference}")
        change_count += len(block["changes"])
        changed_cases += bool(block["changes"])
    return {"reviewed_cases": len(cases), "changed_cases": changed_cases, "changes": change_count}
