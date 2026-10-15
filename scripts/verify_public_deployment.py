"""Verify exact audited static bytes and security headers on the approved Pages host."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

import httpx

HOSTS = (
    "https://aegis-news-showcase.pages.dev",
    "https://daily-preview.aegis-news-showcase.pages.dev",
)


def public_path(name: str) -> str:
    if name == "404.html":
        return "/aegis-public-verification-missing-route"
    if name.endswith("index.html"):
        return "/" + name.removesuffix("index.html")
    return "/" + name


async def verify(base: str) -> None:
    local = json.loads(Path("apps/showcase/dist/data/manifest.json").read_bytes())
    limiter = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        response = await client.get(base + "/data/manifest.json")
        response.raise_for_status()
        if response.json() != local:
            raise ValueError("live manifest differs from the audited build")
        if len(local["files"]) > 2500:
            raise ValueError("live inventory exceeds reviewed ceiling")

        async def asset(name: str, expected: str) -> None:
            if name == "_headers":
                return  # Cloudflare configuration is not served as a public asset.
            if name.startswith("/") or ".." in name or ":" in name:
                raise ValueError("invalid audited asset path")
            async with limiter:
                result = await client.get(base + public_path(name))
                if name == "404.html":
                    if result.status_code not in {200, 404}:
                        raise ValueError("unexpected not-found status")
                else:
                    result.raise_for_status()
                if hashlib.sha256(result.content).hexdigest() != expected:
                    raise ValueError("deployed static asset hash differs: " + name)

        await asyncio.gather(*(asset(name, expected) for name, expected in local["files"].items()))
        root = await client.get(base + "/")
        root.raise_for_status()
        expected_headers = Path("apps/showcase/dist/_headers").read_text().splitlines()[1:]
        for line in expected_headers:
            name, value = line.strip().split(":", 1)
            if root.headers.get(name, "").strip() != value.strip():
                raise ValueError("deployed security header differs: " + name)
        if root.headers.get("set-cookie"):
            raise ValueError("unexpected public authentication/session cookie")
    print(f"Verified {len(local['files']) - 1} deployed public asset hashes and security headers")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", choices=HOSTS, required=True)
    asyncio.run(verify(parser.parse_args().base_url))


if __name__ == "__main__":
    main()
