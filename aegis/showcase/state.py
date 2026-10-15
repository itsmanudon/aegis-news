"""Public-data-only GitHub branch storage with non-forcing compare-and-swap writes."""

import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from aegis.provenance.service import canonical
from aegis.showcase.contracts import DailyExport, Export, PublicExport, parse_export
from aegis.showcase.daily import digest

REPOSITORY = "itsmanudon/aegis-news"
BRANCH = "publication-data"


class StateError(RuntimeError):
    pass


class GitHubState:
    def api(self, method: str, route: str, value: dict[str, Any] | None = None) -> dict[str, Any]:
        command = ["gh", "api", "--method", method, "repos/" + REPOSITORY + "/" + route]
        if value is not None:
            command.extend(["--input", "-"])
        result = subprocess.run(
            command,
            input=json.dumps(value) if value is not None else None,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            # gh error output can contain remote content. Keep it out of publication logs.
            if "HTTP 404" in result.stderr:
                raise FileNotFoundError("public state resource not found")
            raise StateError("GitHub public state operation failed")
        return json.loads(result.stdout)  # type: ignore[no-any-return]

    def head(self) -> str:
        return str(self.api("GET", "git/ref/heads/" + BRANCH)["object"]["sha"])

    def read(self, name: str, head: str | None = None) -> bytes:
        value = self.api("GET", "contents/" + name + "?ref=" + (head or self.head()))
        if value.get("encoding") != "base64":
            value = self.api("GET", "git/blobs/" + str(value["sha"]))
        content = base64.b64decode(value["content"])
        if len(content) > 8 * 1024 * 1024:
            raise StateError("public state file exceeds export limit")
        return content

    def commit(self, files: dict[str, bytes], expected_head: str | None, message: str) -> str:
        if expected_head is not None and self.head() != expected_head:
            raise StateError("public state changed concurrently; refusing overwrite")
        entries = []
        for name, content in files.items():
            if name not in {"dataset.json", "prepared.json"} and not re.fullmatch(
                r"(?:releases|receipts)/[0-9a-f]{64}\.json", name
            ):
                raise StateError("state path is outside the public-data allowlist")
            if len(content) > 8 * 1024 * 1024:
                raise StateError("state file exceeds size ceiling")
            entries.append(
                {
                    "path": name,
                    "mode": "100644",
                    "type": "blob",
                    "sha": self.api(
                        "POST",
                        "git/blobs",
                        {"content": base64.b64encode(content).decode(), "encoding": "base64"},
                    )["sha"],
                }
            )
        tree_request: dict[str, Any] = {"tree": entries}
        if expected_head:
            tree_request["base_tree"] = self.api("GET", "git/commits/" + expected_head)["tree"][
                "sha"
            ]
        tree = self.api("POST", "git/trees", tree_request)["sha"]
        commit = self.api(
            "POST",
            "git/commits",
            {"message": message, "tree": tree, "parents": [expected_head] if expected_head else []},
        )["sha"]
        if expected_head:
            self.api("PATCH", "git/refs/heads/" + BRANCH, {"sha": commit, "force": False})
        else:
            self.api("POST", "git/refs", {"ref": "refs/heads/" + BRANCH, "sha": commit})
        return str(commit)

    def bootstrap(self, export: Export) -> str:
        from aegis.showcase.site import check_trust

        check_trust(export)
        try:
            self.head()
        except FileNotFoundError:
            content = canonical(export.model_dump(mode="json"))
            return self.commit(
                {
                    "dataset.json": content,
                    "prepared.json": b"null",
                    "releases/" + digest(export) + ".json": content,
                },
                None,
                "Initialize validated public publication state",
            )
        raise StateError("public state already exists; refusing to reset history")

    def current(self) -> tuple[str, Export]:
        from aegis.showcase.site import check_trust

        head = self.head()
        export = parse_export(self.read("dataset.json", head))
        check_trust(export)
        if isinstance(export, PublicExport):
            # Legacy signatures bind individual records, not release membership.
            # Pin the complete reviewed bootstrap until the first signed envelope.
            bootstrap = parse_export(Path("apps/showcase/dataset.json").read_bytes())
            if digest(export) != digest(bootstrap):
                raise StateError("legacy state differs from reviewed bootstrap membership")
        return head, export

    def release(self, identity: str) -> DailyExport:
        from aegis.showcase.site import check_trust

        if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
            raise StateError("invalid public release identity")
        result = parse_export(self.read("releases/" + identity + ".json"))
        if not isinstance(result, DailyExport) or digest(result) != identity:
            raise StateError("state release digest/type mismatch")
        check_trust(result)
        return result

    def prepare(self, export: DailyExport, expected: str, *, preview: bool = False) -> str:
        head, previous = self.current()
        if head != expected or export.parent_sha256 != digest(previous):
            raise StateError("release parent does not match validated current state")
        from aegis.showcase.site import check_trust

        check_trust(export)
        if export.sequence != getattr(previous, "sequence", 0) + 1:
            raise StateError("release sequence mismatch")
        pending = json.loads(self.read("prepared.json", head))
        identity = digest(export)
        if pending and pending.get("release") != identity:
            raise StateError("unfinished publication exists; resume it before preparing another")
        files = {"releases/" + identity + ".json": canonical(export.model_dump(mode="json"))}
        if not preview:
            files["prepared.json"] = canonical({"release": identity, "parent": digest(previous)})
        return self.commit(files, head, "Validate public release " + identity[:12])

    def promote(self, identity: str, expected: str) -> str:
        head, previous = self.current()
        export = self.release(identity)
        if head != expected or export.parent_sha256 != digest(previous):
            raise StateError("state changed before release promotion")
        pending = json.loads(self.read("prepared.json", head))
        if pending != {"release": identity, "parent": digest(previous)}:
            raise StateError("release was not prepared for production")
        # Caller must first verify the actual public release digest over HTTPS.
        import httpx

        response = httpx.get("https://aegis-news-showcase.pages.dev/data/manifest.json", timeout=30)
        response.raise_for_status()
        if response.json().get("export_sha256") != identity:
            raise StateError("Cloudflare has not published this validated release")
        return self.commit(
            {
                "dataset.json": canonical(export.model_dump(mode="json")),
                "prepared.json": b"null",
                "receipts/" + identity + ".json": canonical(
                    {
                        "release": identity,
                        "status": "deployed",
                        "url": "https://aegis-news-showcase.pages.dev",
                        "source_commit": export.source_commit,
                    }
                ),
            },
            head,
            "Promote deployed public release " + identity[:12],
        )

    def download(self, output: Path, candidate: Path | None = None) -> dict[str, str]:
        head, previous = self.current()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical(previous.model_dump(mode="json")))
        pending = json.loads(self.read("prepared.json", head))
        result = {"head": head, "current": digest(previous), "resume": "false"}
        if pending:
            export = self.release(pending["release"])
            if (
                pending != {"release": digest(export), "parent": digest(previous)}
                or export.parent_sha256 != digest(previous)
                or export.sequence != getattr(previous, "sequence", 0) + 1
            ):
                raise StateError("prepared state parent mismatch")
            if candidate:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(canonical(export.model_dump(mode="json")))
            result.update({"resume": "true", "release": digest(export)})
        return result

    def verify_live_parent(self, state: dict[str, str]) -> None:
        """Reject state rollback or an independently changed production deployment."""
        import httpx

        response = httpx.get("https://aegis-news-showcase.pages.dev/data/dataset.json", timeout=30)
        response.raise_for_status()
        live = parse_export(response.content)
        from aegis.showcase.site import check_trust

        check_trust(live)
        allowed = {state["current"]}
        if state.get("resume") == "true":
            allowed.add(state["release"])
        if digest(live) not in allowed:
            raise StateError(
                "live release differs from current/prepared state; reconcile explicitly"
            )
