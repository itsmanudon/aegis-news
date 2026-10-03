"""Generate presentation tables and CPU/GPU consistency evidence from measured reports."""

import importlib
import json
from pathlib import Path
from typing import Any

RESULTS = Path("ml/evaluation/results")
OUTPUT = Path("docs/evaluation/evidence/gold-v3")
NAMES = ("offline", "light-cpu", "light-gpu")
METRICS = (
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
    ("Resolution accuracy", "resolution", "accuracy"),
    (
        "Resolution top-3 with abstentions",
        "resolution",
        "top_3_accuracy_including_correct_abstentions",
    ),
    ("Retrieval MRR", "retrieval", "mrr"),
    ("Retrieval recall@3", "retrieval", "recall_at_3"),
)


def read(name: str, suffix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = json.loads((RESULTS / f"gold-v3-{name}{suffix}.json").read_text())
    return result


def compare_predictions(cpu: Any, gpu: Any, path: str = "") -> tuple[list[str], list[float]]:
    if isinstance(cpu, float) and isinstance(gpu, float):
        return [], [abs(cpu - gpu)]
    if isinstance(cpu, dict) and isinstance(gpu, dict) and cpu.keys() == gpu.keys():
        pairs = [compare_predictions(cpu[k], gpu[k], f"{path}.{k}") for k in cpu]
    elif isinstance(cpu, list) and isinstance(gpu, list) and len(cpu) == len(gpu):
        pairs = [
            compare_predictions(a, b, f"{path}.{i}")
            for i, (a, b) in enumerate(zip(cpu, gpu, strict=True))
        ]
    else:
        return ([] if cpu == gpu else [path]), []
    return [x for differences, _ in pairs for x in differences], [
        x for _, deltas in pairs for x in deltas
    ]


def main() -> None:
    profiles = {name: read(name) for name in NAMES}
    if any(not p["quality_metrics_valid_for_whole_profile"] for p in profiles.values()):
        raise ValueError("incomplete quality pass")
    if len({p["dataset_file_sha256"] for p in profiles.values()}) != 1:
        raise ValueError("different dataset bytes")
    differences, deltas = compare_predictions(
        profiles["light-cpu"]["predictions"], profiles["light-gpu"]["predictions"]
    )
    consistency = {
        "dataset_file_sha256": profiles["offline"]["dataset_file_sha256"],
        "categorical_prediction_differences": differences,
        "maximum_absolute_numeric_delta": max(deltas, default=0),
        "quality_metrics_equal": profiles["light-cpu"]["metrics"]
        == profiles["light-gpu"]["metrics"],
        "top_3_rankings_equal": profiles["light-cpu"]["nearest_neighbors"]
        == profiles["light-gpu"]["nearest_neighbors"],
        "numeric_tolerance": 1e-5,
        "protocol": (
            "All output fields compared; exact categorical equality; absolute numeric tolerance "
            "includes embeddings/confidences/sentiment scores. Analysis IDs/timestamps excluded "
            "by existing scorer."
        ),
    }
    (RESULTS / "gold-v3-device-consistency.json").write_text(
        json.dumps(consistency, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if (
        differences
        or max(deltas, default=0) > 1e-5
        or not consistency["quality_metrics_equal"]
        or not consistency["top_3_rankings_equal"]
    ):
        raise ValueError("CPU/GPU differences require investigation: see consistency report")
    lines = [
        "# Gold v3: one independent human reviewer",
        "",
        "16 synthetic CC0 English samples; same labels as v2. No production-quality claim.",
        "",
        "| Task | Offline Gold v3 | Light CPU Gold v3 | Light GPU Gold v3 |",
        "|---|---:|---:|---:|",
    ]
    for label, *keys in METRICS:
        values = []
        for report in profiles.values():
            value: Any = report["metrics"]
            for key in keys:
                value = value[key]
            values.append(f"{value:.4f}")
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines += [
        "",
        "| Profile | Device | Cold document ms | Warm median ms | Warm p95 ms | "
        "Docs/s | Peak RSS MiB | Peak allocated VRAM MiB |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in NAMES:
        r = read(name, "-performance")
        latency = r["warm_document_latency"]
        vram = r["resources"]["vram_peak_allocated_bytes"]
        lines.append(
            f"| {name} | {r['environment']['device']} | {r['cold_first_document_ms']:.2f} | "
            f"{latency['median_ms']:.2f} | {latency['p95_ms']:.2f} | "
            f"{r['warm_documents_per_second']:.2f} | "
            f"{r['resources']['sampled_rss_peak_bytes'] / 1024**2:.1f} | "
            + (f"{vram / 1024**2:.1f}" if vram is not None else "not used")
            + " |"
        )
    lines += [
        "",
        "Cold is an empty process model cache, not flushed OS disk cache. GPU device setup/import",
        "is reported separately; model load includes remaining imports. Three warm rounds (48",
        "sequential seven-task passes) after one full warmup. RSS sampled every 20 ms; VRAM is",
        "the PyTorch process allocator. No isolated GPU-utilization estimate.",
        "Background workload uncontrolled.",
        "",
        "| Pipeline profile | Device | Cold median / p95 ms | Warm median / p95 ms |",
        "|---|---|---:|---:|",
    ]
    for name in NAMES:
        pipeline = read(name, "-pipeline")
        cold, warm = [b["total_pipeline"] for b in pipeline["batches"]]
        lines.append(
            f"| {name} | {pipeline['device']} | {cold['median_ms']:.2f} / {cold['p95_ms']:.2f} | "
            f"{warm['median_ms']:.2f} / {warm['p95_ms']:.2f} |"
        )
    lines += [
        "",
        "Pipeline uses the same five CC0 demo articles/media, not all 16 evaluation cases.",
        "Each profile has one cold and one warm batch, fresh ingestion keys, signature",
        "verification and duplicate checks. With n=5, p95 is the maximum.",
        "Temporal/SQL/storage overhead remains.",
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")
    labels = ["negative", "neutral", "positive", "mixed"]
    figure, axes = plt.subplots(1, 3, figsize=(11, 3.8), layout="constrained")
    for axis, (name, report) in zip(axes, profiles.items(), strict=True):
        matrix = report["metrics"]["sentiment"]["confusion_matrix"]
        data = [[matrix[g].get(p, 0) for p in labels] for g in labels]
        axis.imshow(data, cmap="Blues", vmin=0, vmax=7)
        axis.set_xticks(range(4), labels, rotation=30, ha="right")
        axis.set_yticks(range(4), labels)
        axis.set_xlabel("Predicted")
        axis.set_ylabel("Gold")
        axis.set_title(name)
        for i in range(4):
            for j in range(4):
                axis.text(j, i, str(data[i][j]), ha="center", va="center")
    figure.suptitle("Gold v3 Human: sentiment counts (16 CC0 samples)")
    figure.savefig(
        OUTPUT / "sentiment-confusion.png",
        dpi=140,
        bbox_inches="tight",
        metadata={"Software": "AegisNews"},
    )
    plt.close(figure)


if __name__ == "__main__":
    main()
