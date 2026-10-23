"""Local coordinator failure paths; synthetic signed data, no providers or cloud writes."""

import asyncio
import base64
import json
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegis.provenance.service import canonical
from aegis.showcase import daily, local, site
from aegis.showcase.acquisition import Fetcher, article
from aegis.showcase.contracts import parse_export
from aegis.showcase.daily_contracts import KeyEntry, TrustRegistry
from aegis.showcase.state import GitHubState, StateError


class MemoryState(GitHubState):
    def __init__(self, previous, release):
        self.previous, self.candidate = previous, release
        self.value = "before"
        self.pending = None
        self.lock = None
        self.events = []
        self.flags = []
        self.runs = []
        self.allow_push = True

    def head(self):
        return self.value

    def current(self):
        return self.value, self.previous

    def read(self, name, head=None):
        assert name == "prepared.json"
        return canonical(self.pending)

    def release(self, identity):
        assert identity == daily.digest(self.candidate)
        return self.candidate

    def verify_live_parent(self, state):
        self.events.append("parent-checked")

    def prepare(self, export, expected):
        assert expected == self.value
        assert export.parent_sha256 == daily.digest(self.previous)
        self.pending = {"release": daily.digest(export), "parent": export.parent_sha256}
        self.value = "prepared"
        self.events.append("prepared")
        return self.value

    def promote(self, identity, expected):
        assert expected == self.value
        assert self.pending["release"] == identity
        self.previous = self.candidate
        self.pending = None
        self.value = "promoted"
        self.events.append("promoted")
        return self.value

    def api(self, method, route, value=None):
        if route == "":
            return {
                "full_name": local.REPOSITORY,
                "default_branch": "main",
                "permissions": {"push": self.allow_push},
            }
        if "variables" in route:
            return {"total_count": len(self.flags), "variables": self.flags}
        if route.startswith("actions/runs"):
            return {"total_count": len(self.runs), "workflow_runs": self.runs}
        if route.startswith("git/commits/"):
            return {"tree": {"sha": "public-tree"}}
        if route == "git/commits":
            assert value["tree"] == "public-tree"
            return {"sha": "unique-lease-commit"}
        if method == "POST" and route == "git/refs":
            if self.lock:
                raise StateError("already exists")
            self.lock = value["sha"]
            self.events.append("locked")
            return {}
        if method == "GET" and route == "git/ref/" + local.LOCK:
            if not self.lock:
                raise FileNotFoundError
            return {"object": {"sha": self.lock}}
        if method == "DELETE" and route == "git/refs/" + local.LOCK:
            self.events.append("unlocked")
            self.lock = None
            return {}
        raise AssertionError((method, route))


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    monkeypatch.delenv("AEGIS_PUBLIC_SIGNING_KEY", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_PAGES_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AEGIS_AI_PROFILE", "offline")
    previous = parse_export((site.APP / "dataset.json").read_bytes())
    key = Ed25519PrivateKey.generate()
    registry = TrustRegistry(
        keys={
            "showcase": KeyEntry(public_key=previous.public_key, status="verify-only"),
            "daily-v1": KeyEntry(
                public_key=base64.b64encode(key.public_key().public_bytes_raw()).decode(),
                status="active",
            ),
        }
    )
    app = tmp_path / "apps/showcase"
    app.mkdir(parents=True)
    (app / "trust.json").write_text(
        json.dumps({"key_id": previous.key_id, "public_key": previous.public_key})
    )
    trust = app / "trust-registry.json"
    trust.write_bytes(canonical(registry.model_dump(mode="json")))
    monkeypatch.setattr(site, "APP", app)
    monkeypatch.setattr(daily, "TRUST", trust)
    now = datetime.now(UTC) - timedelta(seconds=1)
    row = article(
        "nasa",
        "Artemis Synthetic Fixture",
        "https://www.nasa.gov/synthetic-local",
        now - timedelta(hours=1),
        now,
    )
    monkeypatch.setattr(
        daily, "acquire", AsyncMock(return_value=([row], {"nasa": "ok", "gdelt": "unavailable"}))
    )
    monkeypatch.setattr(daily, "media", AsyncMock(return_value=[]))

    async def candidate():
        async with httpx.AsyncClient() as client:
            return await daily.candidate(
                previous, daily.DailySigner(key, "daily-v1"), registry, Fetcher(client), now
            )

    export, report = asyncio.run(candidate())
    key_file = tmp_path / ".keys/daily-publication/daily-v1.key"
    key_file.parent.mkdir(parents=True)
    key_file.write_bytes(base64.b64encode(key.private_bytes_raw()))
    publisher = local.LocalPublisher(tmp_path)
    store = MemoryState(previous, export)
    publisher.store = store
    publisher.checkout = Mock(return_value=export.source_commit)
    publisher.github_checks = Mock(return_value="fixture-owner")
    publisher.command = Mock(return_value="")
    publisher.gates = Mock()
    publisher.verify_live = Mock(side_effect=lambda: store.events.append("live-verified"))
    service = SimpleNamespace(
        checkpoint=Mock(
            return_value={
                "deployment_id": "12345678-1234-4234-8234-123456789abc",
                "manifest": {},
                "headers": {},
            }
        ),
        restore=Mock(),
    )

    @contextmanager
    def recovery():
        yield service

    publisher.recovery = recovery
    monkeypatch.setattr(local, "verify", AsyncMock())
    monkeypatch.setattr(local, "audit", Mock())
    monkeypatch.setattr(local.deployment, "preflight", Mock())
    monkeypatch.setattr(
        local.deployment,
        "configuration",
        lambda: {"project": "aegis-news-showcase", "account_id": "fixture"},
    )

    async def acquire(previous_path, output, key_path, report_path):
        output.write_bytes(canonical(export.model_dump(mode="json")))
        report_path.write_bytes(canonical(report))
        return True

    run = AsyncMock(side_effect=acquire)
    monkeypatch.setattr(daily, "run", run)
    return SimpleNamespace(
        p=publisher, store=store, export=export, key=key_file, run=run, service=service
    )


def test_dry_run_never_mutates_remote_state(scenario):
    result = scenario.p.execute(key_file=scenario.key)
    assert result["status"] == "validated dry run; no remote mutation"
    assert result["acquisition"]["source_outcomes"]["gdelt"] == "unavailable"
    assert result["added"] == 1
    assert not scenario.store.lock and scenario.store.pending is None
    assert scenario.store.events == ["parent-checked"]
    scenario.p.command.assert_not_called()


def test_success_orders_live_verification_before_promotion(scenario):
    result = scenario.p.execute(publish=True, key_file=scenario.key)
    assert result["production_changed"] is True and result["promotion_head"] == "promoted"
    assert scenario.store.events.index("live-verified") < scenario.store.events.index("promoted")
    assert scenario.store.pending is None and scenario.store.lock is None
    scenario.service.restore.assert_not_called()
    commands = [c.args[0] for c in scenario.p.command.call_args_list]
    assert commands[-1][-4:] == ["--project-name", "aegis-news-showcase", "--branch", "main"]
    assert all("workflow" not in command for command in commands)


@pytest.mark.parametrize("credential", ["missing", "wrong"])
def test_signing_failure_prevents_acquisition(scenario, credential):
    scenario.key.unlink()
    if credential == "wrong":
        scenario.key.write_bytes(base64.b64encode(Ed25519PrivateKey.generate().private_bytes_raw()))
    with pytest.raises(local.LocalPublicationError, match="Signing preflight"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    scenario.run.assert_not_called()
    assert scenario.store.pending is None


def test_expired_credential_prevents_remote_preparation(scenario, monkeypatch):
    monkeypatch.setattr(local.deployment, "configuration", Mock(side_effect=ValueError("expired")))
    with pytest.raises(ValueError, match="expired"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    scenario.run.assert_not_called()
    assert scenario.store.lock is None and scenario.store.pending is None


def test_stale_state_after_local_gates_prevents_upload(scenario):
    scenario.p.gates.side_effect = lambda *args: setattr(scenario.store, "value", "concurrent")
    with pytest.raises(local.LocalPublicationError, match="state changed during"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    assert scenario.store.pending is None and scenario.store.lock is None


def test_failed_live_check_restores_parent_preserves_pending(scenario):
    scenario.p.verify_live.side_effect = ValueError("synthetic invalid bytes")
    with pytest.raises(local.LocalPublicationError, match="previous release restored"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    scenario.service.restore.assert_called_once()
    assert scenario.store.pending["release"] == daily.digest(scenario.export)
    assert scenario.store.lock is None and "promoted" not in scenario.store.events


def test_failed_upload_uses_the_same_guarded_rollback(scenario):
    def command(args, **kwargs):
        if "deploy" in args:
            raise local.LocalPublicationError("synthetic upload failure")
        return ""

    scenario.p.command.side_effect = command
    with pytest.raises(local.LocalPublicationError, match="previous release restored"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    scenario.service.restore.assert_called_once()
    scenario.p.verify_live.assert_not_called()


def test_failed_recovery_retains_distributed_lock(scenario):
    scenario.p.verify_live.side_effect = ValueError("bad live bytes")
    scenario.service.restore.side_effect = ValueError("bad rollback")
    with pytest.raises(local.LocalPublicationError, match="lock retained"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    assert scenario.store.lock and scenario.store.pending


def test_hard_interruption_keeps_lease_for_explicit_recovery(scenario):
    scenario.p.verify_live.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        scenario.p.execute(publish=True, key_file=scenario.key)
    assert scenario.store.lock and scenario.store.pending


def test_promotion_failure_can_resume_without_reacquisition(scenario):
    original = scenario.store.promote
    scenario.store.promote = Mock(side_effect=StateError("synthetic promotion interruption"))
    with pytest.raises(StateError):
        scenario.p.execute(publish=True, key_file=scenario.key)
    assert scenario.store.pending and scenario.store.lock is None
    scenario.store.promote = original
    scenario.run.reset_mock()
    result = scenario.p.execute(publish=True, key_file=scenario.key)
    assert result["resumed"] and scenario.store.pending is None
    scenario.run.assert_not_called()


def test_no_news_keeps_previous_site_without_prepare(scenario):
    async def no_news(previous, output, key, report):
        report.write_text('{"status":"no new records","source_outcomes":{"gdelt":"unavailable"}}')
        return False

    scenario.run.side_effect = no_news
    result = scenario.p.execute(publish=True, key_file=scenario.key)
    assert result["status"].startswith("no new eligible")
    scenario.p.gates.assert_called_once()
    assert scenario.store.pending is None and not scenario.store.lock


def test_status_reports_pending_and_lock_without_signing(scenario):
    scenario.store.prepare(scenario.export, scenario.store.value)
    scenario.store.lock = "retained-lease"
    scenario.key.unlink()
    result = scenario.p.execute(status=True)
    assert result["pending_release"] == daily.digest(scenario.export)
    assert result["publication_lock"] == "retained-lease"
    scenario.run.assert_not_called()


def test_competing_lease_cannot_be_overwritten(scenario):
    with (
        local.PublicationLease(scenario.store, "before"),
        pytest.raises(local.LocalPublicationError, match="lock unavailable"),
        local.PublicationLease(scenario.store, "before"),
    ):
        pytest.fail("second process acquired the same lease")
    assert scenario.store.lock is None


def test_changed_lease_is_not_deleted_by_old_owner(scenario):
    with (
        pytest.raises(local.LocalPublicationError, match="lock changed"),
        local.PublicationLease(scenario.store, "before"),
    ):
        scenario.store.lock = "different-owner"
    assert scenario.store.lock == "different-owner"


@pytest.mark.parametrize("kind", ["flags", "running", "permissions"])
def test_remote_controls_fail_closed(scenario, kind):
    if kind == "flags":
        scenario.store.flags = [{"name": "DAILY_PUBLICATION_ENABLED", "value": "true"}]
    elif kind == "running":
        scenario.store.runs = [{"name": "Publish Public Showcase", "event": "workflow_dispatch"}]
    else:
        scenario.store.allow_push = False
    with pytest.raises(local.LocalPublicationError):
        local.LocalPublisher.github_checks(scenario.p)


def test_empty_successful_delete_response_is_valid(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr="")
    )
    assert GitHubState().api("DELETE", "git/refs/" + local.LOCK) == {}


def test_repository_lookup_has_no_trailing_slash_or_unneeded_secrets(monkeypatch):
    monkeypatch.setenv("AEGIS_PUBLIC_SIGNING_KEY", "synthetic-private-key")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-pages-token")

    def run(args, **kwargs):
        assert args[-1] == "repos/itsmanudon/aegis-news"
        assert "AEGIS_PUBLIC_SIGNING_KEY" not in kwargs["env"]
        assert "CLOUDFLARE_API_TOKEN" not in kwargs["env"]
        return SimpleNamespace(returncode=0, stdout='{"permissions":{"push":true}}', stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    assert GitHubState().api("GET", "")["permissions"]["push"]


def test_timed_out_upload_keeps_lock_even_after_verified_rollback(scenario):
    def command(args, **kwargs):
        if "deploy" in args:
            raise local.LocalCommandTimeout("synthetic timeout")
        return ""

    scenario.p.command.side_effect = command
    with pytest.raises(local.LocalPublicationError, match="lock retained"):
        scenario.p.execute(publish=True, key_file=scenario.key)
    scenario.service.restore.assert_called_once()
    assert scenario.store.lock and scenario.store.pending


@pytest.mark.parametrize("fault", [None, "dirty", "origin", "workflow", "functions", "stale"])
def test_trusted_checkout_and_no_hosted_trigger_guards(tmp_path, monkeypatch, fault):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    for name in local.WORKFLOWS:
        (workflows / name).write_text((local.ROOT / ".github/workflows" / name).read_text())
    if fault == "workflow":
        with (workflows / "ci.yaml").open("a") as stream:
            stream.write("\n# unreviewed trigger change\n")
    if fault == "functions":
        (tmp_path / "functions").mkdir()
    monkeypatch.chdir(tmp_path)
    publisher = local.LocalPublisher(tmp_path)

    def command(args, **kwargs):
        if "--show-toplevel" in args:
            return str(tmp_path)
        if "get-url" in args:
            return "https://github.com/" + (
                "other/repository.git" if fault == "origin" else local.REPOSITORY + ".git"
            )
        if "--porcelain" in args:
            return " M tracked.py" if fault == "dirty" else ""
        if "--is-ancestor" in args and fault == "stale":
            raise local.LocalPublicationError("main baseline is newer")
        return "a" * 40 if args[-1] == "HEAD" else ""

    publisher.command = Mock(side_effect=command)
    if fault:
        with pytest.raises(local.LocalPublicationError):
            publisher.checkout(dependencies=False)
    else:
        assert publisher.checkout(dependencies=False) == "a" * 40


def test_local_publisher_cannot_be_invoked_by_hosted_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(local.LocalPublicationError, match="must not run inside GitHub Actions"):
        local.LocalPublisher(tmp_path).checkout()


def test_child_processes_receive_only_needed_credentials(tmp_path, monkeypatch):
    for name in ("AEGIS_PUBLIC_SIGNING_KEY", "CLOUDFLARE_API_TOKEN", "GH_TOKEN"):
        monkeypatch.setenv(name, "synthetic-secret")
    seen = []

    def run(args, **kwargs):
        seen.append(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(local.shutil, "which", lambda name: name)
    publisher = local.LocalPublisher(tmp_path)
    publisher.command(["node", "fixed-script.mjs"])
    assert not any(
        n in seen[-1] for n in ("AEGIS_PUBLIC_SIGNING_KEY", "CLOUDFLARE_API_TOKEN", "GH_TOKEN")
    )
    publisher.command(["npx", local.WRANGLER, "pages", "deploy"], cloudflare=True)
    assert seen[-1]["CLOUDFLARE_API_TOKEN"] == "synthetic-secret"
    assert "AEGIS_PUBLIC_SIGNING_KEY" not in seen[-1] and "GH_TOKEN" not in seen[-1]
