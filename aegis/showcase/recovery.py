"""Pin a verified production deployment before upload and restore it on failed checks."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from aegis.provenance.service import canonical
from aegis.showcase.contracts import parse_export
from aegis.showcase.daily import digest
from aegis.showcase.deployment import configuration, preflight
from aegis.showcase.site import check_trust
from scripts.verify_public_deployment import verify

BASE = "https://aegis-news-showcase.pages.dev"
POINT = Path(".data/daily/recovery.json")
HEADER_NAMES = (
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-frame-options",
    "cache-control",
)


class RecoveryError(RuntimeError):
    pass


class PagesRecovery:
    def __init__(self, api: httpx.Client, public: httpx.Client, account: str) -> None:
        # Separate clients ensure the Cloudflare bearer token never reaches a public host.
        self.api = api
        self.public = public
        self.project = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + account
            + "/pages/projects/aegis-news-showcase"
        )

    def request(self, method: str, route: str = "") -> Any:
        response = self.api.request(method, self.project + route)
        if response.status_code != 200 or response.json().get("success") is not True:
            raise RecoveryError("Cloudflare recovery operation failed")
        return response.json()["result"]

    def get(self, base: str, path: str) -> bytes:
        with self.public.stream("GET", base + path, follow_redirects=False) as response:
            if response.status_code != 200:
                raise RecoveryError("recovery evidence unavailable")
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > 8 * 1024 * 1024:
                    raise RecoveryError("recovery evidence exceeds publication boundary")
            return bytes(content)

    def evidence(self, base: str, expected: str) -> dict[str, Any]:
        raw = self.get(base, "/data/dataset.json")
        export = parse_export(raw)
        check_trust(export)
        manifest = json.loads(self.get(base, "/data/manifest.json"))
        if (
            digest(export) != expected
            or manifest.get("export_sha256") != expected
            or manifest.get("files", {}).get("data/dataset.json") != hashlib.sha256(raw).hexdigest()
        ):
            raise RecoveryError("rollback target differs from last validated publication")
        return manifest  # type: ignore[no-any-return]

    @staticmethod
    def deployment_url(deployment: dict[str, Any]) -> str:
        identity = str(UUID(deployment["id"]))
        expected = "https://" + identity[:8] + ".aegis-news-showcase.pages.dev"
        if (
            deployment.get("url") != expected
            or deployment.get("environment") != "production"
            or deployment.get("latest_stage", {}).get("status") != "success"
            or deployment.get("uses_functions")
        ):
            raise RecoveryError("rollback requires a successful static production deployment")
        return expected

    def checkpoint(self, expected: str) -> dict[str, Any]:
        project = self.request("GET")
        deployments = [project.get("canonical_deployment") or {}]
        # On restart the current deployment may already be the prepared candidate.
        # Search a bounded history for the still-authoritative prior publication.
        for page in range(3):
            for deployment in deployments:
                try:
                    url = self.deployment_url(deployment)
                    manifest = self.evidence(url, expected)
                    root = self.public.get(url + "/")
                    root.raise_for_status()
                    headers = {name: root.headers[name] for name in HEADER_NAMES}
                    if root.headers.get("set-cookie"):
                        raise RecoveryError("unexpected session cookie on rollback target")
                    return {
                        "deployment_id": deployment["id"],
                        "release_sha256": expected,
                        "manifest": manifest,
                        "headers": headers,
                    }
                except (RecoveryError, ValueError, KeyError, httpx.HTTPError):
                    continue
            if page < 2:
                deployments = self.request(
                    "GET", f"/deployments?env=production&per_page=10&page={page + 1}"
                )
        raise RecoveryError("no verified production rollback target; refusing upload")

    def restore(self, point: dict[str, Any], expected: str) -> None:
        if point["release_sha256"] != expected:
            raise RecoveryError("rollback checkpoint differs from validated previous state")
        identity = str(UUID(point["deployment_id"]))
        deployment = self.request("GET", "/deployments/" + identity)
        url = self.deployment_url(deployment)
        if self.evidence(url, expected) != point["manifest"]:
            raise RecoveryError("rollback target evidence changed")
        self.request("POST", "/deployments/" + identity + "/rollback")
        for attempt in range(3):
            try:
                if self.evidence(BASE, expected) != point["manifest"]:
                    raise RecoveryError("restored inventory differs from checkpoint")
                asyncio.run(verify(BASE, manifest=point["manifest"], headers=point["headers"]))
                print("Previous validated production deployment restored and byte-verified")
                return
            except (RecoveryError, ValueError, httpx.HTTPError):
                if attempt == 2:
                    raise RecoveryError(
                        "rollback verification failed; owner recovery required"
                    ) from None
                time.sleep(10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("checkpoint", "restore"))
    parser.add_argument("--previous", type=Path, default=Path(".data/daily/previous.json"))
    args = parser.parse_args()
    previous = parse_export(args.previous.read_bytes())
    check_trust(previous)
    preflight()
    config = configuration()
    with (
        httpx.Client(
            timeout=30,
            follow_redirects=False,
            headers={"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"]},
        ) as api,
        httpx.Client(timeout=30, follow_redirects=False) as public,
    ):
        recovery = PagesRecovery(api, public, config["account_id"])
        if args.action == "checkpoint":
            point = recovery.checkpoint(digest(previous))
            asyncio.run(
                verify(
                    "https://"
                    + str(UUID(point["deployment_id"]))[:8]
                    + ".aegis-news-showcase.pages.dev",
                    manifest=point["manifest"],
                    headers=point["headers"],
                )
            )
            POINT.parent.mkdir(parents=True, exist_ok=True)
            POINT.write_bytes(canonical(point))
        else:
            recovery.restore(json.loads(POINT.read_bytes()), digest(previous))


if __name__ == "__main__":
    main()
