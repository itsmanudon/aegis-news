"""Exercise failed-publication rollback without any real Cloudflare mutations."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from aegis.showcase import recovery
from aegis.showcase.contracts import parse_export
from aegis.showcase.daily import digest
from aegis.showcase.site import APP, artifact_bytes

IDENTITY = "12345678-1234-4234-8234-123456789abc"
URL = "https://12345678.aegis-news-showcase.pages.dev"
DEPLOYMENT = {
    "id": IDENTITY,
    "url": URL,
    "environment": "production",
    "latest_stage": {"status": "success"},
    "uses_functions": False,
}


@pytest.fixture
def service(monkeypatch):
    export = parse_export((APP / "dataset.json").read_bytes())
    artifacts = artifact_bytes(export)
    calls = []
    headers = dict.fromkeys(recovery.HEADER_NAMES, "fixture-header")

    def api(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer fixture"
        if request.method == "POST":
            assert request.url.path.endswith("/" + IDENTITY + "/rollback")
            result = DEPLOYMENT
        elif request.url.path.endswith("/deployments/" + IDENTITY):
            result = DEPLOYMENT
        elif request.url.path.endswith("/deployments"):
            result = [DEPLOYMENT]
        else:
            result = {"canonical_deployment": DEPLOYMENT}
        return httpx.Response(200, json={"success": True, "result": result})

    def public(request):
        calls.append(request)
        assert "authorization" not in request.headers
        assert str(request.url).startswith((URL + "/", recovery.BASE + "/"))
        name = request.url.path.lstrip("/")
        return httpx.Response(200, content=artifacts.get(name, b"fixture-root"), headers=headers)

    with (
        httpx.Client(
            transport=httpx.MockTransport(api), headers={"Authorization": "Bearer fixture"}
        ) as api_client,
        httpx.Client(transport=httpx.MockTransport(public)) as public_client,
    ):
        store = recovery.PagesRecovery(api_client, public_client, "fixture-account")
        verifier = AsyncMock()
        monkeypatch.setattr(recovery, "verify", verifier)
        yield store, digest(export), calls, verifier


def test_checkpoint_restore_and_full_byte_verification(service):
    store, expected, calls, verifier = service
    point = store.checkpoint(expected)
    assert point["deployment_id"] == IDENTITY
    assert point["manifest"]["export_sha256"] == expected
    store.restore(point, expected)
    assert sum(r.method == "POST" for r in calls) == 1
    verifier.assert_awaited_once_with(
        recovery.BASE, manifest=point["manifest"], headers=point["headers"]
    )


def test_checkpoint_looks_up_previous_deployment_on_resume(service, monkeypatch):
    store, expected, calls, _ = service
    request = store.request

    def current(method, route=""):
        if not route:
            return {"canonical_deployment": {}}
        return request(method, route)

    monkeypatch.setattr(store, "request", current)
    assert store.checkpoint(expected)["deployment_id"] == IDENTITY
    assert any(r.url.path.endswith("/deployments") for r in calls)


def test_absent_verified_target_blocks_upload_after_bounded_lookup(service):
    store, _, calls, _ = service
    with pytest.raises(recovery.RecoveryError, match="no verified"):
        store.checkpoint("0" * 64)
    assert sum(r.url.path.endswith("/deployments") for r in calls) == 2
    assert not any(r.method == "POST" for r in calls)


@pytest.mark.parametrize(
    "updates",
    [
        {"url": "https://127.0.0.1/private"},
        {"environment": "preview"},
        {"latest_stage": {"status": "failure"}},
        {"uses_functions": True},
        {"id": "../other-project"},
    ],
)
def test_unapproved_rollback_targets_are_rejected(updates):
    with pytest.raises((recovery.RecoveryError, ValueError)):
        recovery.PagesRecovery.deployment_url(DEPLOYMENT | updates)


def test_changed_checkpoint_or_remote_evidence_cannot_trigger_rollback(service):
    store, expected, calls, _ = service
    point = store.checkpoint(expected)
    with pytest.raises(recovery.RecoveryError, match="checkpoint differs"):
        store.restore(point, "0" * 64)
    modified = json.loads(json.dumps(point))
    modified["manifest"]["export_sha256"] = "0" * 64
    with pytest.raises(recovery.RecoveryError, match="evidence changed"):
        store.restore(modified, expected)
    assert not any(r.method == "POST" for r in calls)


def test_failed_restore_verification_is_bounded_and_reported(service, monkeypatch):
    store, expected, _, verifier = service
    point = store.checkpoint(expected)
    verifier.side_effect = ValueError("altered public asset")
    sleeps = []
    monkeypatch.setattr(recovery.time, "sleep", sleeps.append)
    with pytest.raises(recovery.RecoveryError, match="owner recovery required"):
        store.restore(point, expected)
    assert verifier.await_count == 3 and sleeps == [10, 10]
