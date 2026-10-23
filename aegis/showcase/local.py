"""Local orchestration of the existing publisher; no alternative signing or state format."""

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any
from uuid import UUID, uuid4

import httpx

from aegis.provenance.service import canonical
from aegis.showcase import daily, deployment
from aegis.showcase.contracts import DailyExport, Export, parse_export
from aegis.showcase.daily_contracts import TrustRegistry
from aegis.showcase.recovery import BASE, PagesRecovery
from aegis.showcase.site import audit, build, check_trust
from aegis.showcase.state import REPOSITORY, GitHubState, StateError
from scripts.verify_public_deployment import verify

ROOT = Path(__file__).resolve().parents[2]
LOCK = "tags/aegis-local-publication-lock"
FLAGS = {"DAILY_PUBLICATION_ENABLED", "ACTIONS_PAID_USAGE_DISABLED"}
WRANGLER = "wrangler@4.151.0"
WORKFLOWS = {
    "ci.yaml": "2ca40298ea2aa4ecf48d0e8dc0cdf2531101c71f1ea884f0d89c968ed63f9003",
    "daily-publication.yaml": "57309eb0f2d337b58f10068c6ca385a419e49ca3ed92097b7fda4f397b032cce",
    "public-showcase.yaml": "b1013db2395417be5560c55ac1c8291a699feab19210cf0612bcba64d2c17c90",
}


class LocalPublicationError(RuntimeError):
    """Messages contain controlled diagnostics, never subprocess output or secret values."""


class LocalCommandTimeout(LocalPublicationError):
    """A timed-out upload may still finish remotely: retain its distributed lease."""


class PublicationLease:
    """Atomic create-only Git ref; no expiry or automatic stealing after a crash."""

    def __init__(self, store: GitHubState, head: str, run_id: str | None = None):
        self.store, self.head = store, head
        self.run_id = run_id or uuid4().hex
        self.identity: str | None = None
        self.keep = False

    def __enter__(self) -> "PublicationLease":
        # A unique public-only commit prevents an old process deleting a later owner's lock.
        tree = self.store.api("GET", "git/commits/" + self.head)["tree"]["sha"]
        commit = self.store.api(
            "POST",
            "git/commits",
            {
                "tree": tree,
                "parents": [self.head],
                "message": "Local publication lease " + self.run_id,
            },
        )["sha"]
        try:
            self.store.api("POST", "git/refs", {"ref": "refs/" + LOCK, "sha": commit})
        except StateError:
            raise LocalPublicationError(
                "Publication lock unavailable; inspect --status, never steal it"
            ) from None
        self.identity = commit
        return self

    def verify(self) -> None:
        if self.store.api("GET", "git/ref/" + LOCK)["object"]["sha"] != self.identity:
            raise LocalPublicationError("Publication lock changed; stop for explicit recovery")

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if kind and not issubclass(kind, Exception):
            self.keep = True
        if not self.keep:
            self.verify()
            self.store.api("DELETE", "git/refs/" + LOCK)


class LocalPublisher:
    def __init__(self, root: Path = ROOT):
        self.root = root.resolve()
        self.store = GitHubState()
        self.stage = "initialization"
        self.deployment_outcome = "not attempted"

    def command(self, args: list[str], *, cloudflare: bool = False, live: bool = False) -> str:
        """Fixed argv only, no shell; credentials never become command arguments or logs."""
        environment = dict(os.environ)
        for name in ("AEGIS_PUBLIC_SIGNING_KEY", "CLOUDFLARE_API_TOKEN"):
            environment.pop(name, None)
        if args[0] not in {"git", "gh"}:
            environment.pop("GH_TOKEN", None)
            environment.pop("GITHUB_TOKEN", None)
        if cloudflare:
            environment["CLOUDFLARE_API_TOKEN"] = os.environ["CLOUDFLARE_API_TOKEN"]
        environment.update(
            {"AEGIS_AI_PROFILE": "offline", "CI": "true", "WRANGLER_SEND_METRICS": "false"}
        )
        environment.pop("AEGIS_PUBLIC_BASE_URL", None)
        if live:
            environment["AEGIS_PUBLIC_BASE_URL"] = BASE
        executable = shutil.which(args[0])
        if not executable:
            raise LocalPublicationError("Required CLI unavailable: " + args[0])
        try:
            result = subprocess.run(
                [executable, *args[1:]],
                cwd=self.root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise LocalCommandTimeout(
                "Local command timed out; inspect publication status before retry"
            ) from None
        if result.returncode:
            raise LocalPublicationError("Validation command failed during " + self.stage)
        return result.stdout.strip()

    def checkout(self, *, dependencies: bool = True) -> str:
        if os.getenv("GITHUB_ACTIONS"):
            raise LocalPublicationError("local-publish must not run inside GitHub Actions")
        if Path.cwd().resolve() != self.root:
            raise LocalPublicationError("Run from the repository root")
        if Path(self.command(["git", "rev-parse", "--show-toplevel"])).resolve() != self.root:
            raise LocalPublicationError("Unexpected checkout root")
        remote = self.command(["git", "remote", "get-url", "origin"])
        if remote not in {
            "https://github.com/" + REPOSITORY + ".git",
            "https://github.com/" + REPOSITORY,
            "git@github.com:" + REPOSITORY + ".git",
        }:
            raise LocalPublicationError("Checkout origin is not the approved repository")
        if self.command(["git", "status", "--porcelain", "--untracked-files=all"]):
            raise LocalPublicationError(
                "Commit or preserve tracked/unignored changes before publication"
            )
        self.command(["git", "fetch", "--no-tags", "origin", "main"])
        self.command(["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"])
        commit = self.command(["git", "rev-parse", "HEAD"])
        if any(
            (self.root / name).exists()
            for name in (
                "functions",
                "wrangler.toml",
                "wrangler.json",
                "wrangler.jsonc",
            )
        ):
            raise LocalPublicationError("Unexpected root Functions or Wrangler configuration")
        # The existing CI is branch-filtered: neither public-data writes nor lock tags run it.
        workflows = self.root / ".github/workflows"
        if {p.name for p in workflows.iterdir()} != set(WORKFLOWS):
            raise LocalPublicationError(
                "Workflow inventory changed; review local-publication isolation"
            )
        for name, expected in WORKFLOWS.items():
            if hashlib.sha256((workflows / name).read_text().encode()).hexdigest() != expected:
                raise LocalPublicationError(
                    "Workflow bytes changed; review branch/tag trigger isolation"
                )
        ci = (workflows / "ci.yaml").read_text()
        if "branches-ignore: [publication-data]" not in ci or re.search(
            r"(?m)^\s+tags(?:-ignore)?:", ci
        ):
            raise LocalPublicationError(
                "CI branch/tag policy changed; refusing potential hosted usage"
            )
        for name in ("daily-publication.yaml", "public-showcase.yaml"):
            if re.search(r"(?m)^\s+push:", (workflows / name).read_text()):
                raise LocalPublicationError("Unexpected push-triggered publisher")
        if dependencies:
            for name in ("gh", "uv", "node", "pnpm", "npx"):
                if not shutil.which(name):
                    raise LocalPublicationError("Required CLI unavailable: " + name)
            if int(self.command(["node", "--version"]).lstrip("v").split(".")[0]) < 22:
                raise LocalPublicationError("Node.js 22 or newer required")
        return commit

    def github_checks(self) -> str:
        repo = self.store.api("GET", "")
        if (
            repo.get("full_name") != REPOSITORY
            or repo.get("default_branch") != "main"
            or not repo.get("permissions", {}).get("push")
        ):
            raise LocalPublicationError(
                "Authenticated GitHub identity lacks repository write permission"
            )
        for route in ("actions/variables", "environments/public-daily-publication/variables"):
            variables = self.store.api("GET", route + "?per_page=100")
            if variables.get("total_count", 0) > 100 or any(
                v["name"] in FLAGS for v in variables["variables"]
            ):
                raise LocalPublicationError("Publication control variables must remain unset")
        for status in ("queued", "in_progress", "waiting", "requested", "pending"):
            runs = self.store.api("GET", "actions/runs?status=" + status + "&per_page=100")
            if runs.get("total_count", 0) >= 100:
                raise LocalPublicationError("Active workflow lookup ceiling exceeded")
            if any(
                r["name"] in {"Daily Public Publication", "Publish Public Showcase"}
                or (r["name"] == "MVP CI" and r["event"] == "workflow_dispatch")
                for r in runs["workflow_runs"]
            ):
                raise LocalPublicationError("A conflicting hosted publication may be running")
        # gh already uses the credential's selected host/account; keep raw auth output private.
        identity = self.command(["gh", "api", "user", "--jq", ".login"])
        if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", identity):
            raise LocalPublicationError("Authenticated GitHub identity unavailable")
        return identity

    def gates(self, export: Export, directory: Path) -> None:
        self.stage = "publication regression tests"
        with tempfile.TemporaryDirectory(prefix="aegis-publisher-tests-") as temporary:
            self.command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/unit/test_public_showcase.py",
                    "tests/unit/test_daily_publication.py",
                    "tests/unit/test_publication_recovery.py",
                    "tests/unit/test_local_publication.py",
                    "--basetemp",
                    str(Path(temporary) / "pytest"),
                ]
            )
        self.stage = "repository secret guard"
        self.command([sys.executable, "scripts/scan_secrets.py"])
        requirements = directory / "audit-requirements.txt"
        self.stage = "locked production dependency export"
        self.command(
            [
                "uv",
                "export",
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(requirements),
                "--quiet",
            ]
        )
        self.stage = "Python production dependency audit"
        self.command(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--disable-pip",
                "--no-deps",
                "-r",
                str(requirements),
            ]
        )
        self.stage = "Node production dependency audit"
        self.command(["pnpm", "audit", "--prod"])
        self.stage = "static output and browser acceptance"
        build(export, self.root / "apps/showcase/dist")
        audit(export, self.root / "apps/showcase/dist")
        self.command(["node", "apps/showcase/check-browser.mjs"])

    @contextmanager
    def recovery(self) -> Iterator[PagesRecovery]:
        config = deployment.configuration()
        with (
            httpx.Client(
                timeout=30,
                follow_redirects=False,
                headers={"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"]},
            ) as api,
            httpx.Client(timeout=30, follow_redirects=False) as public,
        ):
            yield PagesRecovery(api, public, config["account_id"])

    def verify_live(self) -> None:
        asyncio.run(verify(BASE))
        self.command(["node", "apps/showcase/check-browser.mjs"], live=True)

    def publish(
        self, export: DailyExport, state: dict[str, str], directory: Path, source_commit: str
    ) -> str:
        self.stage = "deployment credential preflight"
        deployment.preflight()
        self.command(["npx", "--yes", WRANGLER, "--version"])
        self.github_checks()
        with PublicationLease(self.store, state["head"], directory.name) as lease:
            (directory / "lease.json").write_bytes(
                canonical({"ref": "refs/" + LOCK, "sha": lease.identity, "run": directory.name})
            )
            self.github_checks()
            if self.store.head() != state["head"]:
                raise LocalPublicationError("Durable state changed; rerun validation")
            self.store.verify_live_parent(state)
            self.stage = "CAS preparation"
            head = (
                state["head"]
                if state["resume"] == "true"
                else self.store.prepare(export, state["head"])
            )
            self.stage = "verified rollback checkpoint"
            with self.recovery() as service:
                point = service.checkpoint(state["current"])
                asyncio.run(
                    verify(
                        "https://"
                        + str(UUID(point["deployment_id"]))[:8]
                        + ".aegis-news-showcase.pages.dev",
                        manifest=point["manifest"],
                        headers=point["headers"],
                    )
                )
                (directory / "recovery.json").write_bytes(canonical(point))
                lease.verify()
                if self.store.head() != head:
                    raise LocalPublicationError("Durable state changed before upload")
                if self.checkout(dependencies=False) != source_commit:
                    raise LocalPublicationError("Source checkout changed before upload")
                self.github_checks()
                audit(export, self.root / "apps/showcase/dist")
                self.store.verify_live_parent(
                    state | {"resume": "true", "release": daily.digest(export)}
                )
                self.stage = "atomic upload and live verification"
                try:
                    config = deployment.configuration()
                    self.deployment_outcome = "upload attempted; outcome unverified"
                    self.command(
                        [
                            "npx",
                            "--yes",
                            WRANGLER,
                            "pages",
                            "deploy",
                            "apps/showcase/dist",
                            "--project-name",
                            config["project"],
                            "--branch",
                            "main",
                        ],
                        cloudflare=True,
                    )
                    self.verify_live()
                    self.deployment_outcome = "live verified; durable promotion pending"
                except Exception as error:
                    try:
                        lease.verify()
                        if self.store.head() != head:
                            raise LocalPublicationError("State changed; automatic rollback refused")
                        service.restore(point, state["current"])
                        self.deployment_outcome = (
                            "previous release restored and verified; pending preserved"
                        )
                    except BaseException:
                        lease.keep = True
                        raise LocalPublicationError(
                            "Recovery could not be verified; "
                            "publication lock retained for owner recovery"
                        ) from None
                    if isinstance(error, LocalCommandTimeout):
                        lease.keep = True
                        raise LocalPublicationError(
                            "Upload timed out; prior checkpoint restored, "
                            "lock retained until remote completion is reconciled"
                        ) from None
                    raise LocalPublicationError(
                        "Publication failed; previous release restored, pending state preserved"
                    ) from None
            self.stage = "durable promotion"
            lease.verify()
            promoted = self.store.promote(daily.digest(export), head)
            final_head, current = self.store.current()
            if (
                final_head != promoted
                or daily.digest(current) != daily.digest(export)
                or json.loads(self.store.read("prepared.json", final_head)) is not None
            ):
                raise LocalPublicationError("Promotion confirmation failed; inspect durable state")
            self.deployment_outcome = "live verified and durably promoted"
            return promoted

    def execute(
        self,
        *,
        publish: bool = False,
        status: bool = False,
        key_file: Path | None = None,
        recheck: str | None = None,
    ) -> dict[str, Any]:
        if recheck is not None and (
            publish or status or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{32}", recheck)
        ):
            raise LocalPublicationError("--recheck accepts a local run ID in dry-run mode only")
        commit = self.checkout(dependencies=not status)
        identity = self.github_checks()
        home = self.root / ".data/local-publication"
        home.mkdir(parents=True, exist_ok=True)
        lock = home / "run.lock"
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise LocalPublicationError(
                "Another local run or interrupted lock exists; "
                "inspect .data/local-publication/run.lock"
            ) from None
        os.close(descriptor)
        directory = home / "runs" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex)
        directory.mkdir(parents=True)
        receipt: dict[str, Any] = {
            "mode": "status" if status else "publish" if publish else "dry-run",
            "source_commit": commit,
            "github_identity": identity,
            "url": BASE,
            "production_changed": False,
            "credentials_present": {
                name: bool(os.getenv(name))
                for name in (
                    "CLOUDFLARE_API_TOKEN",
                    "CLOUDFLARE_ACCOUNT_ID",
                    "CLOUDFLARE_PAGES_PROJECT",
                )
            },
        }
        try:
            self.stage = "validated durable state and live parent"
            state = self.store.download(directory / "previous.json", directory / "candidate.json")
            self.store.verify_live_parent(state)
            receipt.update(
                {
                    "state_head": state["head"],
                    "parent_sha256": state["current"],
                    "resumed": state["resume"] == "true",
                }
            )
            try:
                remote_lock = self.store.api("GET", "git/ref/" + LOCK)["object"]["sha"]
            except FileNotFoundError:
                remote_lock = None
            receipt["publication_lock"] = remote_lock
            if status:
                receipt.update(
                    {
                        "status": "validated state",
                        "pending_release": state.get("release"),
                        "cloudflare_token_present": bool(os.getenv("CLOUDFLARE_API_TOKEN")),
                    }
                )
                return receipt
            if remote_lock:
                raise LocalPublicationError(
                    "Publication lock exists; inspect --status before resuming"
                )
            self.stage = "reviewed signing credential"
            registry = TrustRegistry.model_validate_json(daily.TRUST.read_bytes())
            try:
                daily.signer(
                    key_file or self.root / ".keys/daily-publication/daily-v1.key", registry
                )
            except ValueError as error:
                raise LocalPublicationError("Signing preflight failed: " + str(error)) from None
            receipt["signing_key_matches"] = True
            if publish:
                deployment.configuration()
            os.environ["AEGIS_AI_PROFILE"] = "offline"
            self.stage = "bounded approved acquisition"
            if recheck is not None:
                if state["resume"] == "true":
                    raise LocalPublicationError(
                        "Remote pending release takes priority; omit --recheck"
                    )
                original = home / "runs" / recheck / "candidate.json"
                if original.is_symlink() or not original.resolve().is_relative_to(
                    (home / "runs").resolve()
                ):
                    raise LocalPublicationError(
                        "Recheck candidate must remain in local run storage"
                    )
                content = original.read_bytes()
                if len(content) > 8 * 1024 * 1024:
                    raise LocalPublicationError("Recheck candidate exceeds export limit")
                parse_export(content)
                (directory / "candidate.json").write_bytes(content)
                receipt["rechecked_run"] = recheck
                receipt["acquisition_reused"] = True
            elif state["resume"] != "true":
                changed = asyncio.run(
                    daily.run(
                        directory / "previous.json",
                        directory / "candidate.json",
                        key_file or self.root / ".keys/daily-publication/daily-v1.key",
                        directory / "report.json",
                    )
                )
                receipt["acquisition"] = json.loads((directory / "report.json").read_bytes())
                if not changed:
                    previous = parse_export((directory / "previous.json").read_bytes())
                    self.gates(previous, directory)
                    receipt.update(
                        {
                            "status": "no new eligible records; previous release retained",
                            "records": len(previous.records),
                            "added": 0,
                            "removed": 0,
                            "release_sha256": daily.digest(previous),
                            "static_and_browser_checks": "passed",
                        }
                    )
                    return receipt
            export = parse_export((directory / "candidate.json").read_bytes())
            if not isinstance(export, DailyExport):
                raise LocalPublicationError("Expected a signed daily release")
            check_trust(export, publication=True)
            if state["resume"] != "true" and not recheck and export.source_commit != commit:
                raise LocalPublicationError("Candidate source differs from validated checkout")
            previous = parse_export((directory / "previous.json").read_bytes())
            self.store.validate_successor(export, previous)
            old, new = (
                {r.metadata.id for r in previous.records},
                {r.metadata.id for r in export.records},
            )
            receipt.update(
                {
                    "release_sha256": daily.digest(export),
                    "records": len(export.records),
                    "publishers": len({r.metadata.publisher for r in export.records}),
                    "per_source": dict(Counter(r.metadata.source for r in export.records)),
                    "images": sum(m.reference.kind == "image" for m in export.media),
                    "videos": sum(m.reference.kind == "video" for m in export.media),
                    "added": len(new - old),
                    "removed": len(old - new),
                    "candidate_source_commit": export.source_commit,
                }
            )
            if (directory / "report.json").exists():
                receipt["acquisition"] = json.loads((directory / "report.json").read_bytes())
            self.gates(export, directory)
            receipt["static_and_browser_checks"] = "passed"
            if self.store.head() != state["head"]:
                raise LocalPublicationError(
                    "Durable state changed during validation; start a fresh run"
                )
            if self.checkout(dependencies=False) != commit:
                raise LocalPublicationError("Source checkout changed during validation")
            if publish:
                receipt["production_changed"] = None
                receipt["promotion_head"] = self.publish(export, state, directory, commit)
                receipt["production_changed"] = True
                receipt["status"] = "published, live-verified and durably promoted"
            else:
                receipt["status"] = "validated dry run; no remote mutation"
            return receipt
        except BaseException:
            receipt.update(
                {"status": "failed; inspect state before retry", "failed_stage": self.stage}
            )
            raise
        finally:
            receipt["receipt_path"] = str(directory / "receipt.json")
            receipt["deployment"] = self.deployment_outcome
            (directory / "receipt.json").write_bytes(canonical(receipt) + b"\n")
            (home / "latest.json").write_bytes(canonical(receipt) + b"\n")
            lock.unlink()
