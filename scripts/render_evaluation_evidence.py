"""Render presentation evidence from completed comparable reports; no inference/downloads."""

import importlib
import json
from pathlib import Path
from typing import Any

RESULTS = Path("ml/evaluation/results")
OUTPUT = Path("docs/evaluation/evidence")


def read(name: str, suffix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = json.loads(
        (RESULTS / f"gold-v2-{name}{suffix}.json").read_text(encoding="utf-8")
    )
    return result


def main() -> None:
    profiles = {name: read(name) for name in ("offline", "light")}
    if any(not p["quality_metrics_valid_for_whole_profile"] for p in profiles.values()):
        raise ValueError("incomplete profile is not a pretrained comparison")
    if profiles["offline"]["dataset_sha256"] != profiles["light"]["dataset_sha256"]:
        raise ValueError("profiles must evaluate the identical dataset")
    paths = [
        ("NER span precision", "ner", "span_only", "precision"),
        ("NER span recall", "ner", "span_only", "recall"),
        ("NER span F1", "ner", "span_only", "f1"),
        ("NER typed precision", "ner", "typed", "precision"),
        ("NER typed recall", "ner", "typed", "recall"),
        ("NER typed F1", "ner", "typed", "f1"),
        ("Topic accuracy", "topics", "accuracy"),
        ("Topic macro F1", "topics", "macro_f1"),
        ("Sentiment accuracy", "sentiment", "accuracy"),
        ("Sentiment macro F1", "sentiment", "macro_f1"),
        ("Event precision", "event_extraction", "precision"),
        ("Event recall", "event_extraction", "recall"),
        ("Event F1", "event_extraction", "f1"),
        ("Event classification accuracy", "event_classification", "accuracy"),
        ("Event classification macro F1", "event_classification", "macro_f1"),
        ("Resolution accuracy (gold mentions)", "resolution", "accuracy"),
        (
            "Resolution top-3 (including correct abstentions)",
            "resolution",
            "top_3_accuracy_including_correct_abstentions",
        ),
        ("Retrieval MRR", "retrieval", "mrr"),
        ("Retrieval recall@3", "retrieval", "recall_at_3"),
    ]
    lines = [
        "# Gold v2 CPU comparison",
        "",
        "16 synthetic CC0 items; single agent adjudication, independent human sign-off pending.",
        "No production-quality or held-out real-news claim. Delta = Light minus Offline.",
        "",
        "| Task | Offline | Light | Delta |",
        "|---|---:|---:|---:|",
    ]
    for label, *keys in paths:
        scores = []
        for report in profiles.values():
            value: Any = report["metrics"]
            for key in keys:
                value = value[key]
            scores.append(float(value))
        lines.append(
            f"| {label} | {scores[0]:.4f} | {scores[1]:.4f} | {scores[1] - scores[0]:+.4f} |"
        )
    lines += [
        "",
        "| Profile | Pretrained models | Peak RSS MiB | Snapshot MiB | "
        "Median ms | p95 ms | Docs/s |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    artifacts = read("light", "-artifacts")
    disk = sum(a["selected_artifact_payload_bytes"] for a in artifacts["artifacts"].values())
    for name in profiles:
        result = read(name, "-performance")
        latency = result["warm_document_latency"]
        models = "BERT NER / FinBERT / MiniLM" if name == "light" else "none"
        lines.append(
            f"| {name} | {models} | "
            f"{result['resources']['sampled_rss_peak_bytes'] / 1024**2:.1f} | "
            f"{disk / 1024**2 if name == 'light' else 0:.1f} | "
            f"{latency['median_ms']:.2f} | {latency['p95_ms']:.2f} | "
            f"{result['warm_documents_per_second']:.2f} |"
        )
    lines += [
        "",
        "48 sequential warm seven-task evaluation passes per profile; three rounds of 16 items.",
        "Includes gold-mention resolution and summary classification; excludes storage/Temporal.",
        "RSS sampled every 20 ms includes native allocations; not a guaranteed peak. Disk is",
        "selected model snapshot logical payload, excluding packages, other cached revisions and",
        "filesystem allocation overhead. CPU defaults unchanged; no GPU/VRAM measurement.",
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")
    labels = ["negative", "neutral", "positive", "mixed"]
    figure, axes = plt.subplots(1, 2, figsize=(8, 3.8), layout="constrained")
    for axis, (name, report) in zip(axes, profiles.items(), strict=True):
        matrix = report["metrics"]["sentiment"]["confusion_matrix"]
        data = [[matrix[g].get(p, 0) for p in labels] for g in labels]
        axis.imshow(data, cmap="Blues", vmin=0, vmax=7)
        axis.set_xticks(range(4), labels, rotation=30, ha="right")
        axis.set_yticks(range(4), labels)
        axis.set_xlabel("Predicted")
        axis.set_ylabel("Gold")
        axis.set_title(name.title())
        for row in range(4):
            for col in range(4):
                axis.text(col, row, str(data[row][col]), ha="center", va="center")
    figure.suptitle("Sentiment: same 16 agent-reviewed CC0 items")
    figure.savefig(OUTPUT / "sentiment-confusion.png", dpi=140, metadata={"Software": "AegisNews"})
    plt.close(figure)


if __name__ == "__main__":
    main()
