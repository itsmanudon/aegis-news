import pytest
from fastapi.testclient import TestClient

from aegis.security.abuse import MemoryRateLimiter
from aegis.security.auth import TokenValidator
from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider, generate_development_keys
from aegis.settings import Settings
from apps.api.main import create_app
from scripts.scan_secrets import violations


async def test_rate_limit():
    limiter = MemoryRateLimiter(2)
    assert await limiter.allow("synthetic")
    assert await limiter.allow("synthetic")
    assert not await limiter.allow("synthetic")
    assert await limiter.allow("other")


def test_dev_token_is_explicit_and_standards_compatible(tmp_path):
    generate_development_keys(tmp_path, "dev")
    settings = Settings(
        security_enabled=True,
        dev_identity_enabled=True,
        oidc_issuer="http://localhost:8080",
        oidc_audience="aegis",
        oidc_algorithms=["EdDSA"],
    )
    keys = FileKeyProvider(tmp_path)
    token = issue_development_token(settings, keys, key_id="dev", subject="demo", role="analyst")
    validator = TokenValidator(settings, public_keys={"dev": keys.verification_key("dev")})
    assert validator.validate(token).permits("security:verify")
    with pytest.raises(ValueError):
        issue_development_token(
            settings.model_copy(update={"dev_identity_enabled": False}),
            keys,
            key_id="dev",
            subject="demo",
            role="admin",
        )
    with pytest.raises(ValueError):
        issue_development_token(
            settings.model_copy(update={"environment": "production"}),
            keys,
            key_id="dev",
            subject="demo",
            role="admin",
        )


def test_body_limits_cover_chunked_uploads():
    settings = Settings(
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        security_max_body_bytes=64,
    )
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/security/verify", content=b"x" * 65).status_code == 413
        assert (
            client.post("/api/v1/security/verify", content=iter([b"x" * 40, b"x" * 40])).status_code
            == 413
        )


def test_secret_scanner():
    private = ("-----BEGIN " + "PRIVATE KEY-----\nsynthetic").encode()
    assert violations("example.txt", private)
    assert violations("leaked.pem", b"synthetic")
    assert not violations("docs/example.md", b"Use environment variables for credentials.")
