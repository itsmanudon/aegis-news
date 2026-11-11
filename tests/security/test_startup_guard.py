from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from aegis.contracts.api import DependencyStatus
from aegis.settings import Settings
from apps.api.dependencies import ReadinessProbe
from apps.api.main import create_app

PRODUCTION = dict(
    _env_file=None,
    environment="production",
    allow_insecure_local=False,  # conftest sets the variable for local tests
    security_enabled=True,
    oidc_issuer="https://issuer.test",
    oidc_audience="aegis",
    oidc_jwks_url="https://issuer.test/jwks",
)


def test_api_refuses_to_start_with_security_off(monkeypatch):
    monkeypatch.delenv("AEGIS_ALLOW_INSECURE_LOCAL", raising=False)
    settings = Settings(_env_file=None, security_enabled=False, otel_enabled=False)
    assert not settings.allow_insecure_local
    with pytest.raises(RuntimeError, match="Security is off"), TestClient(create_app(settings)):
        pass


def test_api_starts_with_security_off_only_when_marked_local(monkeypatch):
    monkeypatch.delenv("AEGIS_ALLOW_INSECURE_LOCAL", raising=False)
    settings = Settings(
        _env_file=None, security_enabled=False, allow_insecure_local=True, otel_enabled=False
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200


def test_production_accepts_the_in_memory_rate_limiter():
    settings = Settings(**PRODUCTION, security_rate_backend="memory")
    assert settings.security_rate_backend == "memory"


async def test_readiness_skips_redis_when_the_limiter_does_not_use_it():
    probe = ReadinessProbe(Settings(**PRODUCTION, security_rate_backend="memory"))
    assert probe.redis is None
    with (
        patch.object(probe, "_postgres"),
        patch.object(probe.storage, "ready", AsyncMock()),
    ):
        checks = await probe.check()
    assert [c.name for c in checks] == ["postgres", "object_storage"]
    assert all(isinstance(c, DependencyStatus) and c.ready for c in checks)
    await probe.close()


async def test_readiness_checks_redis_when_the_limiter_uses_it():
    probe = ReadinessProbe(Settings(**PRODUCTION, security_rate_backend="redis"))
    assert probe.redis is not None
    with (
        patch.object(probe, "_postgres"),
        patch.object(probe.storage, "ready", AsyncMock()),
        patch.object(probe.redis, "ping", AsyncMock()),
    ):
        checks = await probe.check()
    assert [c.name for c in checks] == ["postgres", "redis", "object_storage"]
    await probe.close()
