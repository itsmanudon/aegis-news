"""Restartable daily publication candidate generation, never implicit key generation."""

import base64
import hashlib
import json
import math
import os
import subprocess
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from aegis.provenance.service import canonical
from aegis.showcase.acquisition import Fetcher, acquire, media
from aegis.showcase.collection import process
from aegis.showcase.contracts import DailyExport, Export, PublicRecord, parse_export
from aegis.showcase.daily_contracts import KeyEntry, MetadataV2, TrustRegistry

ROOT = Path(__file__).resolve().parents[2]
TRUST = ROOT / "apps/showcase/trust-registry.json"
RETENTION_DAYS = 21
MAX_RECORDS = 300
MAX_NEW = 48


class DailySigner:
    def __init__(self, private: Ed25519PrivateKey, key_id: str) -> None:
        self.private = private
        self.key_id = key_id

    def signing_key(self, key_id: str) -> Ed25519PrivateKey:
        if key_id != self.key_id:
            raise ValueError("wrong signing key identifier")
        return self.private

    def verification_key(self, key_id: str) -> Ed25519PublicKey:
        return self.signing_key(key_id).public_key()

    def encryption_key(self, key_id: str) -> bytes:
        raise ValueError("publication signer has no archive encryption key")

    def next_nonce(self, key_id: str) -> bytes:
        raise ValueError("no archive encryption in publication")


def initialize_key(path: Path, key_id: str = "daily-v1") -> None:
    """Explicit provisioning command; writes only to ignored local .keys."""
    base = (ROOT / ".keys").resolve()
    target = path.resolve()
    if not target.is_relative_to(base) or target.is_symlink():
        raise ValueError("dedicated private signing key must stay under ignored .keys")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("key exists; refusing to rotate or overwrite")
    private = Ed25519PrivateKey.generate()
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(base64.b64encode(private.private_bytes_raw()))
    legacy = json.loads((ROOT / "apps/showcase/trust.json").read_bytes())
    registry = TrustRegistry(
        keys={
            legacy["key_id"]: KeyEntry(public_key=legacy["public_key"], status="verify-only"),
            key_id: KeyEntry(
                public_key=base64.b64encode(private.public_key().public_bytes_raw()).decode(),
                status="active",
            ),
        }
    )
    TRUST.write_bytes(canonical(registry.model_dump(mode="json")) + b"\n")
    print(
        "Dedicated private key created locally. "
        "Only public trust entries were written to the repository."
    )


def signer(path: Path | None, registry: TrustRegistry, key_id: str = "daily-v1") -> DailySigner:
    if os.getenv("GITHUB_ACTIONS") == "true" and (
        os.getenv("GITHUB_REF") != "refs/heads/main"
        or os.getenv("GITHUB_REPOSITORY") != "itsmanudon/aegis-news"
    ):
        raise ValueError("unattended signing is restricted to trusted default-branch workflows")
    secret = os.getenv("AEGIS_PUBLIC_SIGNING_KEY")
    if secret:
        content = secret.encode()
    elif path and path.is_file() and not path.is_symlink():
        content = path.read_bytes()
    else:
        raise ValueError("dedicated signing credential unavailable; no key generated")
    try:
        private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(content, validate=True))
    except ValueError:
        raise ValueError("invalid dedicated signing credential") from None
    entry = registry.keys.get(key_id)
    encoded = base64.b64encode(private.public_key().public_bytes_raw()).decode()
    if not entry or entry.status != "active" or entry.public_key != encoded:
        raise ValueError("signing credential does not match active reviewed public key")
    return DailySigner(private, key_id)


def digest(export: Export) -> str:
    return hashlib.sha256(canonical(export.model_dump(mode="json"))).hexdigest()


def record_time(record: PublicRecord) -> datetime:
    metadata = record.metadata
    return (
        metadata.published_at
        or getattr(metadata, "discovered_at", None)
        or getattr(metadata, "source_updated_at", None)
        or metadata.acquired_at
    )


def balanced(records: list[MetadataV2], limit: int) -> list[MetadataV2]:
    buckets: dict[str, list[MetadataV2]] = defaultdict(list)
    for record in sorted(
        records,
        key=lambda r: (
            r.published_at or r.discovered_at or r.source_updated_at or r.acquired_at,
            r.id,
        ),
        reverse=True,
    ):
        buckets[record.publisher].append(record)
    selected = []
    # Publisher round-robin; at most 8 new references from any publisher per run.
    for index in range(8):
        for publisher in sorted(buckets):
            if index < len(buckets[publisher]):
                selected.append(buckets[publisher][index])
                if len(selected) == limit:
                    return selected
    return selected


async def candidate(
    previous: Export,
    signing: DailySigner,
    registry: TrustRegistry,
    fetcher: Fetcher,
    now: datetime,
) -> tuple[DailyExport | None, dict[str, object]]:
    cutoff = now - timedelta(days=RETENTION_DAYS)
    retained = {r.metadata.id: r for r in previous.records if record_time(r) >= cutoff}
    lookback = min(7, max(2, math.ceil((now - previous.exported_at).total_seconds() / 86400) + 1))
    acquired, outcomes = await acquire(fetcher, now, lookback)
    unique = {r.id: r for r in acquired if r.id not in {x.metadata.id for x in previous.records}}
    selected = balanced(list(unique.values()), MAX_NEW)
    report: dict[str, object] = {
        "source_outcomes": outcomes,
        "acquisition_window_days": lookback,
        "discovered": len(acquired),
        "new_selected": len(selected),
        "selected_per_source": dict(__import__("collections").Counter(r.source for r in selected)),
        "requests": fetcher.requests,
        "pruned": len(previous.records) - len(retained),
    }
    if not selected:
        report["status"] = "no new valid records; previous publication unchanged"
        report["pruned"] = 0
        return None, report
    for value in selected:
        retained[value.id] = await process(value, signing, signing.key_id)
    records = sorted(
        retained.values(), key=lambda r: (record_time(r), r.metadata.id), reverse=True
    )[:MAX_RECORDS]
    if not records:
        raise ValueError(
            "no publishable records remain; retain previous deployment and report stale state"
        )
    references = await media(fetcher, {r.metadata.id: r.metadata.title for r in records}, now)
    if isinstance(previous, DailyExport):
        old_media = {m.reference.id: m for m in previous.media}
        references = [
            m.model_copy(
                update={
                    "reference": m.reference.model_copy(
                        update={"acquired_at": old_media[m.reference.id].reference.acquired_at}
                    )
                }
            )
            if m.reference.id in old_media
            else m
            for m in references
        ]
    body: dict[str, Any] = {
        "version": "aegis-public-2",
        "exported_at": datetime.now(UTC).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "policy": "curated-metadata-links-v2",
        "public_key": registry.keys[signing.key_id].public_key,
        "key_id": signing.key_id,
        "trust": registry.model_dump(mode="json"),
        "parent_sha256": digest(previous),
        "sequence": getattr(previous, "sequence", 0) + 1,
        "records": [
            r.model_dump(mode="json") for r in sorted(records, key=lambda r: r.metadata.id)
        ],
        "media": [
            m.model_dump(mode="json") for m in sorted(references, key=lambda m: m.reference.id)
        ],
    }
    export = sign_release(body, signing)
    report.update(
        {
            "status": "candidate validated",
            "records": len(export.records),
            "images": sum(m.reference.kind == "image" for m in export.media),
            "videos": sum(m.reference.kind == "video" for m in export.media),
            "requests": fetcher.requests,
            "export_sha256": digest(export),
        }
    )
    return export, report


def sign_release(body: dict[str, Any], signing: DailySigner) -> DailyExport:
    body = {k: v for k, v in body.items() if k != "release_signature"}
    # Round-trip first so Pydantic's canonical datetime representation is signed.
    # Parsing the unsigned body through field types avoids signing a different timestamp format.
    from pydantic import TypeAdapter

    fields: dict[str, Any] = {
        k: TypeAdapter(DailyExport.model_fields[k].annotation).validate_python(v)
        for k, v in body.items()
    }
    provisional = DailyExport.model_construct(**fields, release_signature="")
    unsigned = canonical(provisional.model_dump(mode="json", exclude={"release_signature"}))
    body["release_signature"] = base64.b64encode(signing.private.sign(unsigned)).decode()
    return DailyExport.model_validate(body)


async def run(previous_path: Path, output: Path, key_path: Path | None, report_path: Path) -> bool:
    from aegis.showcase.site import check_trust

    if output.exists():
        raise ValueError(
            "candidate output already exists; choose a fresh path to avoid stale reuse"
        )
    previous = parse_export(previous_path.read_bytes())
    check_trust(previous)
    registry = TrustRegistry.model_validate_json(TRUST.read_bytes())
    signing = signer(key_path, registry)
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=False,
        headers={"User-Agent": "AegisNewsAcademic/0.2 (https://github.com/itsmanudon/aegis-news)"},
    ) as client:
        result, report = await candidate(
            previous, signing, registry, Fetcher(client), datetime.now(UTC)
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical(report) + b"\n")
    if result is None:
        return False
    check_trust(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result.model_dump(mode="json")) + b"\n")
    return True
