from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import ValidationError

from aegis.security.auth import TokenValidator, product_access, require_scopes
from aegis.settings import Settings
from apps.api.main import create_app


@pytest.fixture
def identity():
    key = Ed25519PrivateKey.generate()
    settings = Settings(
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        oidc_algorithms=["EdDSA"],
    )
    validator = TokenValidator(settings, public_keys={"test": key.public_key()})

    def token(**changes):
        now = datetime.now(UTC)
        claims = dict(
            iss=settings.oidc_issuer,
            aud="aegis",
            sub="synthetic",
            iat=now,
            exp=now + timedelta(minutes=5),
            scope="documents:read",
            roles=["viewer"],
        )
        claims.update(changes)
        return jwt.encode(claims, key, algorithm="EdDSA", headers={"kid": "test", "typ": "at+jwt"})

    return settings, validator, token


def test_valid_identity_and_scope_policy(identity):
    _, validator, token = identity
    principal = validator.validate(token())
    assert principal.subject == "synthetic"
    assert principal.permits("documents:read")
    assert not principal.permits("sources:write")
    # Role alone does not expand the access token's delegated scope.
    assert not validator.validate(token(scope="", roles=["admin"])).permits("admin:users")
    assert validator.validate(token(scope="sources:write", roles=["source_manager"])).permits(
        "sources:write"
    )
    assert not validator.validate(token(scope="sources:write")).permits("sources:write")
    service = validator.validate(token(idtyp="app", client_id="stockwise-future", roles=[]))
    assert service.kind == "service"
    assert service.permits("documents:read")


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"aud": "other"},
        {"iss": "https://evil.test"},
        {"nbf": datetime.now(UTC) + timedelta(hours=1)},
        {"sub": ""},
        {"roles": "admin"},
        {"scope": ["documents:read"]},
    ],
)
def test_invalid_claims(identity, claims):
    _, validator, token = identity
    with pytest.raises(ValueError, match="Invalid access token"):
        validator.validate(token(**claims))


def test_invalid_signature_and_algorithm(identity):
    _, validator, token = identity
    for value in [
        token() + "bad",
        jwt.encode({"sub": "x"}, "synthetic-only" * 3, algorithm="HS256"),
        jwt.encode({"sub": "x"}, "", algorithm="none"),
    ]:
        with pytest.raises(ValueError):
            validator.validate(value)


def test_api_boundaries_and_headers(identity):
    settings, validator, token = identity
    app = create_app(settings)
    app.state.token_validator = validator
    app.add_api_route(
        "/test/read", lambda: {"ok": True}, dependencies=[require_scopes("documents:read")]
    )
    with TestClient(app) as client:
        assert client.get("/test/read").status_code == 401
        denied = client.get("/test/read", headers={"Authorization": "Bearer " + token(scope="")})
        assert denied.status_code == 403
        valid = client.get("/test/read", headers={"Authorization": "Bearer " + token()})
        assert valid.status_code == 200
        assert valid.headers["x-content-type-options"] == "nosniff"
        preflight = client.options(
            "/test/read",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert preflight.status_code == 200
        assert client.get("/api/v1/security/me").status_code == 401


def test_production_rejects_dev_and_insecure_configuration():
    common = dict(
        environment="production",
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        oidc_jwks_url="https://issuer.test/jwks",
        security_rate_backend="redis",
    )
    assert Settings(**common).security_enabled
    for changes in [
        dict(dev_identity_enabled=True),
        dict(oidc_jwks_url="http://localhost/keys"),
        dict(cors_origins=["*"]),
    ]:
        with pytest.raises(ValidationError):
            Settings(**{**common, **changes})


def test_product_access_requires_every_named_scope(identity):
    settings, validator, token = identity
    app = create_app(settings)
    app.state.token_validator = validator
    app.add_api_route(
        "/test/bundle",
        lambda: {"ok": True},
        dependencies=[product_access("documents:read", "events:read")],
    )
    with pytest.raises(ValueError):
        product_access()
    with pytest.raises(ValueError):
        product_access("documents:read", "not:a-scope")
    with TestClient(app) as client:
        assert client.get("/test/bundle").status_code == 401
        for scope, status in (
            ("documents:read", 403),
            ("events:read", 403),
            ("documents:read events:read", 200),
        ):
            headers = {"Authorization": "Bearer " + token(scope=scope)}
            assert client.get("/test/bundle", headers=headers).status_code == status, scope


def test_feed_scope_is_separate_from_document_scopes(identity):
    settings, validator, token = identity
    app = create_app(settings)
    app.state.token_validator = validator
    app.add_api_route(
        "/test/feed", lambda: {"ok": True}, dependencies=[product_access("feed:read")]
    )

    def bearer(scope):
        service = token(scope=scope, roles=[], idtyp="app", client_id="stockviz-sync")
        return {"Authorization": "Bearer " + service}

    with TestClient(app) as client:
        # The document scopes no longer open the feed or the listings it joins to.
        wide = bearer("documents:read events:read")
        assert client.get("/api/v1/feed/documents", headers=wide).status_code == 403
        assert client.get("/api/v1/assets/mappings", headers=wide).status_code == 403
        # A feed-only token is authorized for a feed route and for nothing that returns text.
        narrow = bearer("feed:read")
        assert client.get("/test/feed", headers=narrow).status_code == 200
        assert client.get("/api/v1/documents", headers=narrow).status_code == 403
        assert client.get("/api/v1/events", headers=narrow).status_code == 403
        # A user needs a role that includes the scope, as for every other scope.
        user = {"Authorization": "Bearer " + token(scope="feed:read", roles=["source_manager"])}
        assert client.get("/test/feed", headers=user).status_code == 403
        viewer = {"Authorization": "Bearer " + token(scope="feed:read", roles=["viewer"])}
        assert client.get("/test/feed", headers=viewer).status_code == 200


def test_token_lifetime_is_capped(identity):
    settings, validator, token = identity
    now = datetime.now(UTC)
    limit = timedelta(seconds=settings.oidc_max_token_lifetime)
    assert validator.validate(token(iat=now, exp=now + limit)).subject == "synthetic"
    for changes in (
        dict(iat=now, exp=now + limit + timedelta(seconds=1)),
        # Backdating iat cannot stretch a token: the bound is on exp - iat.
        dict(iat=now - timedelta(days=30), exp=now + timedelta(minutes=5)),
        dict(iat=now + timedelta(minutes=10), exp=now + timedelta(minutes=5)),
    ):
        with pytest.raises(ValueError, match="Invalid access token"):
            validator.validate(token(**changes))
    short = TokenValidator(
        settings.model_copy(update={"oidc_max_token_lifetime": 60}),
        public_keys=validator.public_keys,
    )
    with pytest.raises(ValueError, match="Invalid access token"):
        short.validate(token())
    with pytest.raises(ValidationError):
        Settings(oidc_max_token_lifetime=0)
