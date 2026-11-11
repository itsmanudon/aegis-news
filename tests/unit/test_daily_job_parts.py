"""The daily job's own logic. The full run is in tests/integration/test_daily_job.py."""

import base64
import stat
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from aegis.jobs.daily import DirectGateway, JobReport, signing_keys, temporal_cli
from aegis.providers.models import ProviderOutcome, ProviderRun
from aegis.security.keys import FileKeyProvider
from aegis.settings import Settings

NOW = datetime(2026, 1, 5, tzinfo=UTC)


def report(*outcomes, failed=()):
    run = ProviderRun(run_id="r", created_at=NOW, status="submitted", outcomes=outcomes)
    return JobReport(started_at=NOW, finished_at=NOW, run=run, failed=failed)


def test_the_job_succeeds_only_when_every_provider_and_workflow_did():
    ok = ProviderOutcome(provider="newsdata", status="submitted")
    budget = ProviderOutcome(provider="gnews", status="failed", error="daily_budget_reached")
    assert report(ok).ok and report(ok, budget).ok
    assert not report(ok, failed=("ingestion-x",)).ok
    assert not report(ProviderOutcome(provider="newsdata", status="disabled")).ok
    assert not report(
        ProviderOutcome(provider="newsdata", status="failed", error="authentication")
    ).ok


def test_a_signing_key_from_the_environment_becomes_private_key_files():
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    settings = Settings(_env_file=None, provenance_key_id="daily", provenance_signing_key=pem)
    with signing_keys(settings) as scoped:
        folder = scoped.security_key_directory
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
        for suffix in ("ed25519.key", "ed25519.pub"):
            assert stat.S_IMODE((folder / f"daily.{suffix}").stat().st_mode) == 0o600
        provider = FileKeyProvider(folder)
        provider.verification_key("daily").verify(provider.signing_key("daily").sign(b"x"), b"x")
    assert not folder.exists()
    # Without a key in the environment the configured directory is used as before.
    plain = Settings(_env_file=None)
    with signing_keys(plain) as unchanged:
        assert unchanged is plain


def test_a_signing_key_that_is_not_ed25519_is_refused():
    with (
        pytest.raises(ValueError),
        signing_keys(Settings(_env_file=None, provenance_signing_key="not a key")),
    ):
        pass


def test_the_cli_must_be_installed():
    with pytest.raises(FileNotFoundError):
        temporal_cli(Settings(_env_file=None, temporal_cli_path="no-such-temporal"))


def test_job_settings_are_bounded():
    for changes in ({"job_limit": 31}, {"job_providers": []}, {"job_timeout_seconds": 5}):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **changes)


class Repository:
    def __init__(self):
        self.sources = []

    def create_source(self, source):
        self.sources.append(source)
        return source


class Submissions:
    def __init__(self):
        self.requests = []

    async def submit(self, request):
        self.requests.append(request)
        return {"workflow_id": "ingestion-1"}


async def test_the_gateway_creates_sources_and_validates_before_submitting():
    repository, submissions = Repository(), Submissions()
    gateway = DirectGateway(repository, submissions)
    created = await gateway.request(
        "POST", "/api/v1/sources", {"name": "Pub", "kind": "web", "url": "https://pub.test/"}
    )
    assert created == {"source_id": repository.sources[0].source_id}
    body = {
        "source_id": created["source_id"],
        "idempotency_key": "live:test:1",
        "content_type": "text/plain",
        "content_base64": base64.b64encode(b"Synthetic headline").decode(),
        "first_seen_at": NOW.isoformat(),
    }
    assert await gateway.request("POST", "/api/v1/ingestions", body) == {
        "workflow_id": "ingestion-1"
    }
    with pytest.raises(ValueError):
        await gateway.request(
            "POST", "/api/v1/ingestions", {**body, "content_base64": "not base64!"}
        )
    with pytest.raises(ValueError):
        await gateway.request("DELETE", "/api/v1/sources", {})
    assert len(submissions.requests) == 1
