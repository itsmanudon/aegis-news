from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from aegis.security.auth import TokenValidator
from aegis.settings import Settings
from apps.api.main import create_app


def test_provider_controls_deny_anonymous_and_insufficient_scope_before_acquisition():
    key = Ed25519PrivateKey.generate()
    settings = Settings(
        _env_file=None,
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        oidc_algorithms=["EdDSA"],
        gnews_api_key="test-secret",
    )
    app = create_app(settings)
    app.state.token_validator = TokenValidator(settings, public_keys={"test": key.public_key()})
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.oidc_issuer,
            "aud": "aegis",
            "sub": "synthetic",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "roles": ["analyst"],
            "scope": "documents:read",
        },
        key,
        algorithm="EdDSA",
        headers={"kid": "test", "typ": "at+jwt"},
    )
    client = TestClient(app)
    for path in (
        "/api/v1/providers/gnews/fetch",
        "/api/v1/providers/fetch-all",
        "/api/v1/youtube-references/refresh",
    ):
        assert client.post(path, json={"limit": 1}).status_code == 401
        denied = client.post(path, json={"limit": 1}, headers={"Authorization": "Bearer " + token})
        assert denied.status_code == 403
        assert "test-secret" not in denied.text
    assert client.get("/api/v1/providers").status_code == 401
    assert client.get("/api/v1/provider-runs/unknown").status_code == 401
    assert not hasattr(app.state, "provider_runner")
