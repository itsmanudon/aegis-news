"""Export a reproducibility manifest or explicitly download configured model snapshots."""

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from aegis.intelligence.common import IMPLEMENTATION_VERSION, configuration_hash
from aegis.intelligence.config import Profile, profile
from aegis.intelligence.local_runtime import LocalRuntime
from aegis.intelligence.taxonomy import EVENTS, NEGATIVE, POSITIVE, TOPICS


def registry_manifest(specs: Profile, *, download: bool = False) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "implementation": IMPLEMENTATION_VERSION,
        "profile": specs.model_dump(),
        "libraries": LocalRuntime().metadata,
        "taxonomies": {"topics": TOPICS, "events": EVENTS},
        "lexicon": {"positive": POSITIVE, "negative": NEGATIVE},
        "artifacts": {},
    }
    manifest["registry_hash"] = configuration_hash(manifest)
    if download:
        hub = importlib.import_module("huggingface_hub")
        seen = set()
        for spec in (specs.ner, specs.topic, specs.sentiment, specs.event, specs.embedding):
            key = f"{spec.model_name}@{spec.revision}"
            if spec.backend == "baseline" or key in seen:
                continue
            seen.add(key)
            files = hub.list_repo_files(repo_id=spec.model_name, revision=spec.revision)
            weights = (
                "*.safetensors"
                if any(f.endswith(".safetensors") for f in files)
                else ("pytorch_model.bin")
            )
            snapshot = Path(
                hub.snapshot_download(
                    repo_id=spec.model_name,
                    revision=spec.revision,
                    allow_patterns=[
                        "*.json",
                        weights,
                        "vocab.txt",
                        "merges.txt",
                        "tokenizer.model",
                        "*.txt",
                    ],
                )
            )
            checksums = {}
            for path in sorted(snapshot.rglob("*")):
                if path.is_file():
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    checksums[str(path.relative_to(snapshot))] = digest.hexdigest()
            manifest["artifacts"][key] = checksums
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("offline", "light", "full"), default="light")
    parser.add_argument("--config", type=Path, help="custom immutable Profile JSON")
    parser.add_argument("--download", action="store_true", help="explicitly allow weight downloads")
    parser.add_argument("--manifest", type=Path, help="write manifest rather than printing JSON")
    args = parser.parse_args()
    specs = (
        Profile.model_validate_json(args.config.read_text())
        if args.config
        else profile(args.profile)
    )
    result = json.dumps(registry_manifest(specs, download=args.download), indent=2, sort_keys=True)
    if args.manifest:
        args.manifest.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
