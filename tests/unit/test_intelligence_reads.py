"""Read contracts validate opaque identities, temporal windows and authorization."""

import base64
import importlib
import importlib.util
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from aegis.settings import Settings
from apps.api.main import create_app


def read_module():
    assert importlib.util.find_spec("aegis.intelligence.read_models") is not None
    return importlib.import_module("aegis.intelligence.read_models")


def test_topic_identity_preserves_exact_label_and_model_configuration():
    reads = read_module()
    identity = ("technology/AI", "synthetic", "topics", "1", "0" * 64)
    encoded = reads.topic_id(identity)
    assert reads.parse_topic_id(encoded) == identity
    assert reads.topic_id(("Technology/AI", *identity[1:])) != encoded
    assert reads.topic_id((*identity[:-1], "1" * 64)) != encoded
    for invalid in ("x", encoded + "=", "topic_v1_W10", "topic_v1_" + "x" * 5000):
        with pytest.raises(ValueError):
            reads.parse_topic_id(invalid)


def test_topic_identity_roundtrips_maximum_canonical_strings():
    reads = read_module()
    exact = ("\u0001" * 512, "\u0002" * 512, "\u0003" * 512, "\u0004" * 512, "0" * 64)
    assert reads.parse_topic_id(reads.topic_id(exact)) == exact


def test_topic_identity_rejects_nul_before_database_binding():
    reads = read_module()
    exact = ("technology", "synthetic", "topic-model", "1", "0" * 64)
    for field in range(4):
        invalid = list(exact)
        invalid[field] += "\u0000"
        with pytest.raises(ValueError):
            reads.parse_topic_id(reads.topic_id(tuple(invalid)))


def test_cursor_freezes_cutoff_and_rejects_filter_or_order_replay():
    reads = read_module()
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    filters = {"kind": "discovery", "order": "published_at", "q": "Atlas"}
    value = reads.encode_cursor(cutoff, filters, [None, "doc_example"])
    assert reads.decode_cursor(value, filters, None) == (cutoff, [None, "doc_example"])
    with pytest.raises(ValueError):
        reads.decode_cursor(value, {**filters, "q": "Other"}, None)
    with pytest.raises(ValueError):
        reads.decode_cursor(value, filters, cutoff + timedelta(days=1))
    for invalid in ("x", value + "=", "e30"):
        with pytest.raises(ValueError):
            reads.decode_cursor(invalid, filters, None)


def test_intelligence_routes_require_document_read_authorization():
    app = create_app(
        Settings(
            _env_file=None,
            security_enabled=True,
            oidc_issuer="https://issuer.test",
            oidc_audience="aegis",
        )
    )
    client = TestClient(app)
    for path in (
        "/topics",
        "/topics/invalid",
        "/topics/invalid/documents",
        "/discovery",
        "/analytics",
    ):
        assert client.get("/api/v1" + path).status_code == 401


def test_analytics_requires_aware_bounded_half_open_interval():
    app = create_app(Settings(_env_file=None, security_enabled=False))
    client = TestClient(app)
    for params in (
        {},
        {"start": "2026-01-01", "end": "2026-01-02"},
        {"start": "2026-01-02T00:00:00Z", "end": "2026-01-01T00:00:00Z"},
        {"start": "2024-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"},
    ):
        response = client.get("/api/v1/analytics", params=params)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_ARGUMENT"


def test_discovery_requires_paired_dates_and_rejects_invalid_cursor():
    app = create_app(Settings(_env_file=None, security_enabled=False))
    client = TestClient(app)
    for params in (
        {"start": "2026-01-01T00:00:00Z"},
        {"order": "event_occurrence"},
        {"cursor": "invalid"},
        {"topic_id": "invalid"},
        {"q": "x" * 201},
        {"limit": 101},
    ):
        assert client.get("/api/v1/discovery", params=params).status_code == 422


def test_opaque_values_reject_deep_json_and_boolean_cursor_versions():
    reads = read_module()
    nested = base64.urlsafe_b64encode(("[" * 4000 + "0" + "]" * 4000).encode()).decode().rstrip("=")
    with pytest.raises(ValueError):
        reads.parse_topic_id("topic_v1_" + nested)
    filters = {"kind": "discovery"}
    invalid = {
        "v": True,
        "as_of": "2026-01-01T00:00:00+00:00",
        "filters": reads.fingerprint(filters),
        "key": [],
    }
    raw = json.dumps(invalid, separators=(",", ":")).encode()
    cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    with pytest.raises(ValueError):
        reads.decode_cursor(cursor, filters, None)


def test_document_cursor_requires_string_timestamp_and_strict_document_id():
    reads = read_module()
    filters = {
        "kind": "discovery",
        "order": "published_at",
        "q": "",
        "source_id": None,
        "topic_id": None,
        "start": None,
        "end": None,
        "time_basis": "published_at",
    }
    client = TestClient(create_app(Settings(_env_file=None, security_enabled=False)))
    for key in ([0, "doc_00000000-0000-0000-0000-000000000001"], [None, "doc_bad"]):
        cursor = reads.encode_cursor(datetime(2026, 1, 1, tzinfo=UTC), filters, key)
        assert client.get("/api/v1/discovery", params={"cursor": cursor}).status_code == 422
