"""Authenticated local API client. Provider credentials stay inside the API service."""

import argparse
import asyncio
import json
import os
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from scripts.demo import compose_command


def identity(token_env: str | None) -> str:
    if token_env:
        token = os.environ.get(token_env, "")
        if not token:
            raise ValueError("token environment variable is empty")
        return token
    result = subprocess.run(
        compose_command(
            "exec",
            "-T",
            "api",
            "python",
            "scripts/security_dev.py",
            "token",
            "--key-id",
            "local",
            "--role",
            "admin",
            "--subject",
            "live-provider-cli",
        ),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("fetch", "fetch-all", "demo", "status", "refresh-youtube")
    )
    parser.add_argument("--provider", choices=("newsdata", "gnews", "newsapi", "gdelt", "youtube"))
    parser.add_argument("--limit", "--limit-per-provider", type=int, default=3)
    parser.add_argument("--query", default="technology")
    parser.add_argument("--country", choices=("in", "us"))
    parser.add_argument("--api-url", default="http://127.0.0.1:38000")
    parser.add_argument("--token-env")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 30:
        parser.error("limit must be 1..30; YouTube is additionally capped at 10")
    if args.command == "fetch" and not args.provider:
        parser.error("fetch requires --provider")
    url = urlsplit(args.api_url)
    if (
        url.scheme != "http"
        or url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        parser.error("explicit loopback API required")
    async with httpx.AsyncClient(
        base_url=args.api_url, timeout=60, follow_redirects=False, trust_env=False
    ) as client:

        async def request(method: str, path: str, body: object = None) -> dict[str, Any]:
            token = await asyncio.to_thread(identity, args.token_env)
            result = await client.request(
                method, path, json=body, headers={"Authorization": "Bearer " + token}
            )
            if not result.is_success:
                raise ValueError("Local provider API HTTP " + str(result.status_code))
            return dict(result.json()["data"])

        if args.command == "refresh-youtube":
            print(json.dumps(await request("POST", "/api/v1/youtube-references/refresh")))
            return
        if args.command == "status":
            if not args.run_id:
                parser.error("status requires --run-id")
            report = await request("GET", "/api/v1/provider-runs/" + args.run_id)
        else:
            path = (
                "/api/v1/providers/" + args.provider + "/fetch"
                if args.command == "fetch"
                else "/api/v1/providers/fetch-all"
            )
            report = await request(
                "POST",
                path,
                {
                    "query": args.query,
                    "limit": args.limit,
                    "country": args.country,
                    "retry_failed": args.retry_failed,
                },
            )
            print(json.dumps({"run_id": report["run_id"], "status": report["status"]}), flush=True)
        started = time.monotonic()
        while not args.no_wait and time.monotonic() - started < 900:
            report = await request("GET", "/api/v1/provider-runs/" + report["run_id"])
            states = report["workflow_statuses"]
            if report["status"] != "running" and all(
                v not in {"RUNNING", "UNAVAILABLE"} for v in states.values()
            ):
                break
            await asyncio.sleep(5)
        print(json.dumps(report, indent=2))
        if (
            report["status"] in {"running", "interrupted"}
            or not any(outcome["status"] == "submitted" for outcome in report["outcomes"])
            or any(
                v in {"RUNNING", "UNAVAILABLE", "FAILED", "TIMED_OUT", "TERMINATED", "CANCELED"}
                for v in report["workflow_statuses"].values()
            )
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (ValueError, httpx.RequestError, subprocess.CalledProcessError) as exc:
        # Do not print HTTP requests, response bodies, tokens or subprocess output.
        raise SystemExit(
            "Provider CLI failed (" + type(exc).__name__ + "); inspect safe run status"
        ) from None
