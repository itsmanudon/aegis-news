"""Optional CPU/CUDA quality pass with unchanged assessment scoring."""

import argparse
import asyncio
import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from aegis.intelligence.assessment import assess, load_assessment
from aegis.intelligence.engine import build_engine
from aegis.intelligence.models import registry_manifest
from scripts.benchmark_profiles import verify_manifest
from scripts.evaluation_device import cuda_module, device_profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("offline", "light"), required=True)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    parser.add_argument(
        "--dataset", type=Path, default=Path("ml/datasets/gold/assessment-v3-human.json")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("ml/datasets/gold/manifest-v3-human.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_manifest(args.manifest)
    if args.dataset.as_posix() not in manifest["files"]:
        raise ValueError("dataset not covered by manifest")
    torch = cuda_module(args.device)
    specs = device_profile(args.profile, args.device)
    report = asyncio.run(
        assess(load_assessment(args.dataset), args.profile, 1, engine=build_engine(specs))
    )
    report["dataset_file_sha256"] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    report["registry"] = registry_manifest(specs)
    try:
        torch_version = version("torch")
    except PackageNotFoundError:
        torch_version = "uninstalled"
    report["environment"].update(
        device=args.device,
        gpu=torch.cuda.get_device_name(0) if torch else "not used",
        cuda_runtime=torch.version.cuda if torch else None,
        torch_version=torch_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not report["quality_metrics_valid_for_whole_profile"]:
        raise SystemExit("profile incomplete: inspect failures; do not claim pretrained quality")


if __name__ == "__main__":
    main()
