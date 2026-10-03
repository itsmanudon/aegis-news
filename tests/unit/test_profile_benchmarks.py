import hashlib
import json
from types import SimpleNamespace

import pytest

from aegis.settings import Settings
from scripts.benchmark_pipeline_profiles import validate_local_target, wait_worker
from scripts.benchmark_profiles import verify_manifest


def test_manifest_verification_rejects_same_size_tampering(tmp_path):
    data = tmp_path / "gold.json"
    data.write_bytes(b"original")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"files": {str(data): {"bytes": 8, "sha256": hashlib.sha256(b"original").hexdigest()}}}
        )
    )
    verify_manifest(manifest)
    data.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="dataset integrity failure"):
        verify_manifest(manifest)


def test_pipeline_benchmark_refuses_remote_database_even_with_local_api():
    settings = Settings(_env_file=None, dev_identity_enabled=True)
    validate_local_target(settings, "http://localhost:38000")
    with pytest.raises(ValueError, match="all be local"):
        validate_local_target(
            Settings(
                _env_file=None,
                dev_identity_enabled=True,
                database_url="postgresql+psycopg://fixture@remote.invalid/news",
            ),
            "http://localhost:38000",
        )


@pytest.mark.asyncio
async def test_worker_readiness_ignores_stale_pollers():
    identities = iter(["old-worker", "evaluation-current-worker"])
    calls = []

    async def describe(request):
        calls.append(request)
        return SimpleNamespace(pollers=[SimpleNamespace(identity=next(identities))])

    client = SimpleNamespace(workflow_service=SimpleNamespace(describe_task_queue=describe))
    worker = SimpleNamespace(pid=123, poll=lambda: None)
    await wait_worker(client, worker, Settings(_env_file=None), "evaluation-current-worker")
    assert len(calls) == 2
