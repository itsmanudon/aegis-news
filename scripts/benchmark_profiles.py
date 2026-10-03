"""Optional local evaluation only: process-cold loading, warm latency and sampled RSS."""

import argparse
import asyncio
import hashlib
import importlib
import json
import platform
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from threading import Event, Thread
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from aegis.domain.models import AnalysisResult, EntityMention, NewsEvent
from aegis.intelligence.assessment import AssessmentCase, latency_report, load_assessment
from aegis.intelligence.config import ModelSpec
from aegis.intelligence.engine import build_engine
from aegis.intelligence.errors import NoPredictions
from aegis.intelligence.extensions import EventClassifier
from aegis.intelligence.local_runtime import LocalRuntime
from aegis.intelligence.providers import TaskProvider
from aegis.intelligence.resolution import Resolver
from scripts.evaluation_device import cuda_module, device_profile, synchronize


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for filename, expected in manifest["files"].items():
        content = Path(filename).read_bytes()
        if (
            len(content) != expected["bytes"]
            or hashlib.sha256(content).hexdigest() != expected["sha256"]
        ):
            raise ValueError(f"dataset integrity failure: {filename}")
    return manifest


class TimedRuntime(LocalRuntime):
    """Instrument the existing loader without changing inference specifications."""

    def __init__(self) -> None:
        super().__init__()
        self.load_ms: dict[str, float] = {}
        self.loaded_devices: dict[str, str] = {}

    def _load(self, task: str, spec: ModelSpec) -> Any:
        started = time.perf_counter()
        loaded = super()._load(task, spec)
        if task not in self.load_ms:
            self.load_ms[task] = (time.perf_counter() - started) * 1000
            self.loaded_devices[task] = str(loaded.device)
            if spec.device.startswith("cuda") and not self.loaded_devices[task].startswith("cuda"):
                raise RuntimeError(f"{task} model did not load on requested CUDA device")
        return loaded


async def benchmark(
    name: str, dataset_path: Path, rounds: int, device: str = "cpu"
) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("positive warm rounds required")
    dataset = load_assessment(dataset_path)
    device_started = time.perf_counter()
    torch = cuda_module(device)
    device_setup_ms = (time.perf_counter() - device_started) * 1000
    if torch is not None:
        torch.cuda.reset_peak_memory_stats()
    specs = device_profile(name, device)
    # Optional packages are imported only when this explicitly invoked benchmark runs.
    psutil = importlib.import_module("psutil")
    process = psutil.Process()
    rss_start = process.memory_info().rss
    rss_samples = [rss_start]
    stop = Event()

    def sample_memory() -> None:
        while not stop.wait(0.02):
            rss_samples.append(process.memory_info().rss)

    sampler = Thread(target=sample_memory, daemon=True)
    sampler.start()
    runtime = TimedRuntime()
    setup_start = time.perf_counter()
    engine = build_engine(specs)
    # Keep the engine's baseline routing; instrument only its shared local backend.
    for provider in (
        engine.entities,
        engine.topics,
        engine.sentiment,
        engine.embeddings,
        engine.events,
    ):
        if isinstance(provider, TaskProvider) and isinstance(provider.runtime, LocalRuntime):
            provider.runtime = runtime
    setup_ms = (time.perf_counter() - setup_start) * 1000
    stages: dict[str, list[float]] = {}
    rows: list[dict[str, Any]] = []
    empty_findings = 0

    async def document_pass(case: AssessmentCase, measured: bool) -> dict[str, float]:
        nonlocal empty_findings
        sample, document = case.sample, case.sample.document
        mentions = tuple(
            EntityMention(
                mention_id="mention_" + str(uuid5(NAMESPACE_URL, f"{document.document_id}:{i}")),
                document_id=document.document_id,
                surface=m.extraction.surface,
                start_offset=m.extraction.start_offset,
                end_offset=m.extraction.end_offset,
                evidence_kind="fact",
            )
            for i, m in enumerate(sample.mentions)
        )
        resolver = Resolver(aliases=sample.aliases)
        event = NewsEvent(
            event_id="evt_" + str(uuid5(NAMESPACE_URL, document.document_id)),
            summary=sample.event_summary or document.text,
            document_ids=(document.document_id,),
            created_at=document.created_at,
            available_at=document.created_at,
            evidence_kind="fact",
        )
        calls: dict[str, Callable[[], Awaitable[AnalysisResult]]] = {
            "entities": lambda: engine.entities.extract(document),
            "topics": lambda: engine.topics.classify(document),
            "sentiment": lambda: engine.sentiment.analyze(document),
            "embedding": lambda: engine.embeddings.embed(document),
            "resolution": lambda: resolver.resolve(document, mentions, sample.candidates),
            "events": lambda: engine.events.extract(document, ()),
        }
        if not isinstance(engine.events, EventClassifier):
            raise TypeError("benchmark requires existing event classification provider")
        classifier = engine.events
        calls["event_classification"] = lambda: classifier.classify(document, event)
        durations = {}
        for task, call in calls.items():
            synchronize(torch)
            started = time.perf_counter()
            try:
                await call()
            except NoPredictions:
                empty_findings += 1
            synchronize(torch)
            duration = (time.perf_counter() - started) * 1000
            durations[task] = duration
            if measured:
                stages.setdefault(task, []).append(duration)
        return durations

    try:
        cold_start = time.perf_counter()
        cold = await document_pass(dataset.cases[0], False)
        cold_ms = (time.perf_counter() - cold_start) * 1000
        load_vram = torch.cuda.memory_allocated() if torch else None
        # A complete unmeasured pass removes shape/document-specific first-use overhead.
        for case in dataset.cases:
            await document_pass(case, False)
        warm_rss = process.memory_info().rss
        batch_start = time.perf_counter()
        for iteration in range(rounds):
            for case in dataset.cases:
                started = time.perf_counter()
                timings = await document_pass(case, True)
                rows.append(
                    {
                        "round": iteration + 1,
                        "document_id": case.sample.document.document_id,
                        "total_ms": (time.perf_counter() - started) * 1000,
                        "stages_ms": timings,
                    }
                )
        batch_seconds = time.perf_counter() - batch_start
    finally:
        rss_samples.append(process.memory_info().rss)
        stop.set()
        sampler.join()
    packages = ["psutil", "torch", "transformers", "sentence-transformers", "huggingface-hub"]
    return {
        "profile": name,
        "dataset_file_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "dataset_version": dataset.version,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "logical_cpus": psutil.cpu_count(),
            "physical_cpus": psutil.cpu_count(logical=False),
            "ram_bytes": psutil.virtual_memory().total,
            "device": device,
            "gpu": torch.cuda.get_device_name(0) if torch else None,
            "cuda_runtime": torch.version.cuda if torch else None,
            "packages": {p: version(p) for p in packages},
            "torch_threads": importlib.import_module("torch").get_num_threads()
            if name == "light"
            else None,
        },
        "engine_construction_ms": setup_ms,
        "device_setup_ms": device_setup_ms,
        "cold_first_document_ms": cold_ms,
        "cold_task_ms": cold,
        "model_load_ms_including_imports": runtime.load_ms,
        "loaded_model_devices": runtime.loaded_devices,
        "warm_rounds": rounds,
        "warm_documents": rows,
        "warm_document_latency": latency_report([r["total_ms"] for r in rows]),
        "warm_task_latency": {task: latency_report(values) for task, values in stages.items()},
        "warm_batch_seconds": batch_seconds,
        "warm_documents_per_second": len(rows) / batch_seconds,
        "resources": {
            "rss_before_model_load_bytes": rss_start,
            "rss_after_warmup_bytes": warm_rss,
            "sampled_rss_peak_bytes": max(rss_samples),
            "sampling_interval_ms": 20,
            "vram_after_cold_document_bytes": load_vram,
            "vram_allocated_bytes": torch.cuda.memory_allocated() if torch else None,
            "vram_reserved_bytes": torch.cuda.memory_reserved() if torch else None,
            "vram_peak_allocated_bytes": torch.cuda.max_memory_allocated() if torch else None,
            "vram_peak_reserved_bytes": torch.cuda.max_memory_reserved() if torch else None,
        },
        "empty_findings_including_warmup": empty_findings,
        "protocol": (
            "Separate fresh Python process per profile; existing providers/specs unchanged; "
            "cold means empty process model cache, NOT flushed OS disk cache; imports included "
            "in first model load; one unmeasured full dataset warmup; sequential seven-task "
            "gold-mention evaluation passes, not full ingestion pipeline; no tracemalloc; "
            "20-ms RSS polling is sampled process memory, not guaranteed native peak; "
            "inference failures except valid empty findings abort the run"
            "; CUDA timings synchronize before/after each task; VRAM stats are this process's "
            "PyTorch allocator, not total display/background GPU memory"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("offline", "light"), required=True)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/gold/assessment-v2.json"))
    parser.add_argument("--manifest", type=Path, default=Path("ml/datasets/gold/manifest-v2.json"))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_manifest(args.manifest)
    expected = manifest["files"].get(args.dataset.as_posix())
    if expected is None:
        raise ValueError("benchmark dataset must be covered by the reviewed manifest")
    report = asyncio.run(benchmark(args.profile, args.dataset, args.rounds, args.device))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
