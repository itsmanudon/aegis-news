"""Adversarial tests for the intentionally narrow public publication boundary."""

import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegis.provenance.service import canonical
from aegis.showcase.collection import metadata, save_collection
from aegis.showcase.contracts import parse_export
from aegis.showcase.site import APP, artifact_bytes, audit, check_trust, date, pages


@pytest.fixture
def raw() -> dict:
    return json.loads((APP / "dataset.json").read_bytes())


def test_frozen_export_is_genuine_verifiable_and_deterministic(raw: dict) -> None:
    export = parse_export(canonical(raw))
    check_trust(export)
    assert 1 <= len(export.records) <= 100
    assert artifact_bytes(export) == artifact_bytes(parse_export(canonical(raw)))
    for record in export.records:
        assert record.metadata.publisher == "NASA"
        assert all(a.provider == "local-baseline" for a in record.analyses)
        assert set(record.model_dump()) == {"metadata", "analyses", "provenance"}


@pytest.mark.parametrize("field", ["access_token", "body", "archive", "audit", "private_key"])
def test_rejects_private_fields_at_every_boundary(raw: dict, field: str) -> None:
    for target in (raw, raw["records"][0], raw["records"][0]["metadata"]):
        attack = copy.deepcopy(raw)
        if target is raw:
            attack[field] = "never publish"
        elif target is raw["records"][0]:
            attack["records"][0][field] = "never publish"
        else:
            attack["records"][0]["metadata"][field] = "never publish"
        with pytest.raises(ValueError):
            parse_export(canonical(attack))


@pytest.mark.parametrize("part", ["metadata", "analysis", "signature", "chain", "missing"])
def test_rejects_tampered_and_incomplete_evidence(raw: dict, part: str) -> None:
    record = raw["records"][0]
    if part == "metadata":
        record["metadata"]["title"] += " changed"
    elif part == "analysis":
        record["analyses"][0]["outputs"][0]["confidence"] = 0.123
    elif part == "signature":
        record["provenance"]["signature"] = base64.b64encode(b"x" * 64).decode()
    elif part == "chain":
        record["provenance"]["chain_hashes"][0] = "0" * 64
    else:
        record["provenance"]["records"].pop()
    with pytest.raises(ValueError):
        parse_export(canonical(raw))


def test_rejects_duplicate_records_and_duplicate_json_fields(raw: dict) -> None:
    raw["records"].append(raw["records"][0])
    with pytest.raises(ValueError):
        parse_export(canonical(raw))
    with pytest.raises(ValueError, match="duplicate JSON"):
        parse_export(b'{"version":"aegis-public-1","version":"other"}')


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nasa.gov/story/",
        "https://www.nasa.gov.evil.test/",
        "https://127.0.0.1/story/",
        "https://www.nasa.gov/story/?token=secret",
    ],
)
def test_rejects_nonapproved_links(raw: dict, url: str) -> None:
    raw["records"][0]["metadata"]["url"] = url
    with pytest.raises(ValueError):
        parse_export(canonical(raw))


def test_pinned_key_cannot_be_substituted(raw: dict) -> None:
    key = Ed25519PrivateKey.generate()
    raw["public_key"] = base64.b64encode(key.public_key().public_bytes_raw()).decode()
    # Even a fully re-signed export must match the independently reviewed trust file.
    for record in raw["records"]:
        body = {k: v for k, v in record["provenance"].items() if k != "signature"}
        record["provenance"]["signature"] = base64.b64encode(key.sign(canonical(body))).decode()
    export = parse_export(canonical(raw))
    with pytest.raises(ValueError, match="trust anchor"):
        check_trust(export)


def test_deduplication_preserves_actual_first_acquisition(tmp_path: Path) -> None:
    first = metadata("nasa", "NASA Test Headline", "https://www.nasa.gov/test/", None)
    second = metadata("nasa", "NASA Changed Headline", "https://www.nasa.gov/test/", None)
    path = tmp_path / "collection.json"
    assert save_collection(path, [first, second]) == 1
    assert (
        json.loads(path.read_bytes())[0]["acquired_at"]
        == first.model_dump(mode="json")["acquired_at"]
    )
    assert date(None) == "Unknown"


def test_output_inventory_detects_any_extra_file(raw: dict, tmp_path: Path) -> None:
    export = parse_export(canonical(raw))
    for name, content in artifact_bytes(export).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    audit(export, tmp_path)
    (tmp_path / "private-dump.txt").write_text("not allowed")
    with pytest.raises(ValueError, match="allowlisted"):
        audit(export, tmp_path)


def test_every_route_and_public_hash_matches(raw: dict) -> None:
    export = parse_export(canonical(raw))
    artifacts = artifact_bytes(export)
    manifest = json.loads(artifacts["data/manifest.json"])
    assert manifest["export_sha256"] == hashlib.sha256(artifacts["data/dataset.json"]).hexdigest()
    assert len(pages(export)) >= 49
    for path, digest in manifest["files"].items():
        assert hashlib.sha256(artifacts[path]).hexdigest() == digest
