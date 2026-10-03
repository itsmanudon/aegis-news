import hashlib
import sys
from types import SimpleNamespace

from aegis.intelligence.config import profile
from aegis.intelligence.models import registry_manifest


def test_manifest_export_is_offline_and_reproducible(monkeypatch):
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)
    first = registry_manifest(profile("light"))
    second = registry_manifest(profile("light"))
    assert first == second
    assert first["artifacts"] == {}
    assert len(first["registry_hash"]) == 64
    assert first["profile"]["embedding"]["dimensions"] == 384


def test_explicit_download_pins_revision_and_hashes_artifacts(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_bytes(b"synthetic")
    calls = []

    def snapshot_download(**kwargs):
        calls.append((kwargs["repo_id"], kwargs["revision"]))
        assert len(kwargs["revision"]) == 40
        return str(tmp_path)

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(
            snapshot_download=snapshot_download,
            list_repo_files=lambda **kwargs: ["config.json", "model.safetensors"],
        ),
    )
    manifest = registry_manifest(profile("full"), download=True)
    assert len(calls) == len(set(calls)) == 4
    assert all(
        value["config.json"] == hashlib.sha256(b"synthetic").hexdigest()
        for value in manifest["artifacts"].values()
    )
