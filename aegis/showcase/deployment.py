"""Fail-closed checks for the one approved, static-only Cloudflare destination."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

ROOT = Path(__file__).resolve().parents[2]


def configuration() -> dict[str, str]:
    config = json.loads((ROOT / "apps/showcase/deployment.json").read_bytes())
    for name, expected in (
        ("CLOUDFLARE_ACCOUNT_ID", config["account_id"]),
        ("CLOUDFLARE_PAGES_PROJECT", config["project"]),
    ):
        if os.getenv(name) != expected:
            raise ValueError(
                "deployment destination is missing or differs from reviewed configuration"
            )
    if not os.getenv("CLOUDFLARE_API_TOKEN"):
        raise ValueError("deployment credential is missing")
    expiry = datetime.fromisoformat(config["expires_at"])
    if datetime.now(UTC) >= expiry:
        raise ValueError("reviewed deployment credential expired; rotate before publication")
    if config["permissions"] != ["Cloudflare Pages Write"]:
        raise ValueError("ambiguous or over-scoped credential attestation")
    return config  # type: ignore[no-any-return]


def preflight() -> None:
    config = configuration()
    headers = {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"]}
    with httpx.Client(timeout=30, follow_redirects=False, headers=headers) as client:
        base = "https://api.cloudflare.com/client/v4/accounts/" + config["account_id"]
        verification = client.get(base + "/tokens/verify")
        if verification.status_code != 200:
            raise ValueError("account-owned deployment credential could not be verified")
        result = verification.json().get("result", {})
        if result.get("status") != "active" or result.get("id") != config["token_id"]:
            raise ValueError(
                "deployment credential identity/status differs from reviewed attestation"
            )
        live_expiry = result.get("expires_on")
        if not live_expiry:
            raise ValueError("deployment credential has ambiguous expiration")
        expiry = datetime.fromisoformat(live_expiry.replace("Z", "+00:00"))
        if (
            not expiry.tzinfo
            or expiry <= datetime.now(UTC)
            or expiry.astimezone(ZoneInfo("Asia/Kolkata")).date()
            != datetime.fromisoformat(config["expires_at"]).date()
        ):
            raise ValueError(
                "deployment credential expiration "
                + expiry.isoformat()
                + " differs from the reviewed 14 January 2027 IST date"
            )
        print("Verified deployment credential expiry (UTC): " + expiry.astimezone(UTC).isoformat())
        # The token cannot inspect its own permission policies without adding token-read access.
        # Rotation/scope changes therefore require a fresh owner-reviewed attestation in Git.
        project = client.get(base + "/pages/projects/" + config["project"])
        if project.status_code != 200:
            raise ValueError("approved Pages project is unavailable")
        data = project.json().get("result", {})
        if data.get("production_branch") != "main" or data.get("source"):
            raise ValueError("Pages project must remain Direct Upload with production branch main")
        for env in data.get("deployment_configs", {}).values():
            if env.get("env_vars") or any(
                env.get(key)
                for key in (
                    "kv_namespaces",
                    "durable_object_namespaces",
                    "d1_databases",
                    "r2_buckets",
                    "services",
                    "ai_bindings",
                    "vectorize_bindings",
                )
            ):
                raise ValueError("unexpected runtime resources in static Pages project")
    print("Approved account-owned Pages credential and static destination verified")
