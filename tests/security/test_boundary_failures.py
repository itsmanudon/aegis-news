import base64
import json
import logging
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from aegis.domain.ids import new_id
from aegis.domain.models import ProvenanceRecord
from aegis.observability.logging import JsonFormatter
from aegis.security.auth import TokenValidator
from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider, generate_development_keys
from aegis.settings import Settings
from apps.api.main import create_app


def test_rsa_public_pem_and_required_claims():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    settings = Settings(
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        oidc_public_keys={"rsa": public},
    )
    validator = TokenValidator(settings)
    now = datetime.now(UTC)
    claims = dict(
        iss=settings.oidc_issuer,
        aud="aegis",
        sub="synthetic",
        iat=now,
        exp=now + timedelta(minutes=5),
        roles=["viewer"],
        scope="documents:read",
    )
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "rsa", "typ": "at+jwt"})
    assert validator.validate(token).permits("documents:read")
    import pytest

    for missing in ["exp", "iat", "sub", "iss", "aud"]:
        value = jwt.encode(
            {k: v for k, v in claims.items() if k != missing},
            key,
            algorithm="RS256",
            headers={"kid": "rsa", "typ": "at+jwt"},
        )
        with pytest.raises(ValueError):
            validator.validate(value)


def test_verification_api_scope_audit_and_invalid_input(tmp_path, caplog):
    generate_development_keys(tmp_path, "dev")
    keys = FileKeyProvider(tmp_path)
    settings = Settings(
        security_enabled=True,
        dev_identity_enabled=True,
        oidc_issuer="http://localhost:8080",
        oidc_audience="aegis",
        oidc_algorithms=["EdDSA"],
        security_key_directory=tmp_path,
    )
    app = create_app(settings)
    app.state.token_validator = TokenValidator(
        settings, public_keys={"dev": keys.verification_key("dev")}
    )
    token = issue_development_token(
        settings, keys, key_id="dev", subject="demo", role="security_auditor"
    )
    viewer = issue_development_token(settings, keys, key_id="dev", subject="viewer", role="viewer")
    record = ProvenanceRecord(
        provenance_id=new_id("prov"),
        subject_id=new_id("raw"),
        input_ids=(),
        operation="raw",
        recorded_at=datetime.now(UTC),
        content_hash=app.state.provenance.crypto.hash(b"synthetic"),
    )
    manifest = app.state.provenance.sign((record,), key_id="dev")
    body = dict(
        manifest=manifest.model_dump(mode="json"),
        contents={record.subject_id: base64.b64encode(b"synthetic").decode()},
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + token}
        assert client.post("/api/v1/security/verify", json=body).status_code == 401
        assert (
            client.post(
                "/api/v1/security/verify", json=body, headers={"Authorization": "Bearer " + viewer}
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/security/audit", headers={"Authorization": "Bearer " + viewer}
            ).status_code
            == 403
        )
        result = client.post("/api/v1/security/verify", json=body, headers=headers)
        assert result.status_code == 200 and result.json()["data"]["valid"]
        events = client.get("/api/v1/security/audit", headers=headers).json()["data"]
        assert {"integrity_verification", "signature_verification"} <= {e["action"] for e in events}
        bad = client.post(
            "/api/v1/security/verify",
            json={**body, "contents": {record.subject_id: "invalid!"}},
            headers=headers,
        )
        assert bad.status_code == 422 and "invalid!" not in bad.text
        assert client.get("/api/v1/security/audit?limit=999", headers=headers).status_code == 422
        assert (
            client.get(
                "/api/v1/security/me", headers={**headers, "Origin": "https://evil.test"}
            ).headers.get("access-control-allow-origin")
            is None
        )
    assert token not in caplog.text
    assert viewer not in caplog.text


def test_rate_failure_closed_and_unauthenticated_rate_limits():
    settings = Settings(
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        security_rate_limit=1,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/security/me").status_code == 401
        limited = client.get("/api/v1/security/me")
        assert limited.status_code == 429 and limited.headers["retry-after"] == "60"

        class Unavailable:
            async def allow(self, identity):
                raise ConnectionError("private-internal-details")

        app.state.rate_limiter = Unavailable()
        response = client.get("/api/v1/security/me")
        assert response.status_code == 503 and "private-internal-details" not in response.text


def test_log_formatter_redacts_bearer_tokens_and_credential_fields():
    record = logging.LogRecord(
        "test",
        logging.INFO,
        "test",
        1,
        "Authorization: Bearer synthetic-private-token "
        "password=synthetic-password token=synthetic-token",
        (),
        None,
    )
    message = json.loads(JsonFormatter().format(record))["message"]
    assert "synthetic-private-token" not in message
    assert "synthetic-password" not in message
    assert "synthetic-token" not in message
