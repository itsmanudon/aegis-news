"""OAuth2 resource server: authenticate signed access tokens; authorize separately."""

from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from aegis.settings import Settings

ROLE_SCOPES = {
    "admin": frozenset(
        {
            "documents:read",
            "events:read",
            "sources:read",
            "sources:write",
            "audit:read",
            "security:verify",
            "admin:users",
        }
    ),
    "analyst": frozenset({"documents:read", "events:read", "sources:read", "security:verify"}),
    "viewer": frozenset({"documents:read", "events:read", "sources:read"}),
    "source_manager": frozenset({"sources:read", "sources:write"}),
    "security_auditor": frozenset({"audit:read", "security:verify"}),
}
KNOWN_SCOPES = ROLE_SCOPES["admin"]


@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str
    roles: frozenset[str]
    scopes: frozenset[str]
    kind: str = "user"
    client_id: str | None = None

    def permits(self, scope: str) -> bool:
        if scope not in KNOWN_SCOPES or scope not in self.scopes:
            return False
        if self.kind == "service":
            return True  # Explicit delegated scopes, provisioned by the trusted issuer.
        return any(scope in ROLE_SCOPES.get(role, ()) for role in self.roles)


class TokenValidator:
    def __init__(self, settings: Settings, *, public_keys: dict[str, Any] | None = None) -> None:
        self.settings = settings
        self.public_keys = public_keys if public_keys is not None else settings.oidc_public_keys
        self.jwks = (
            jwt.PyJWKClient(settings.oidc_jwks_url, timeout=3, lifespan=300)
            if settings.oidc_jwks_url
            else None
        )

    def validate(self, token: str) -> Principal:
        try:
            if not self.settings.security_enabled or len(token) > 16384:
                raise ValueError
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if (
                algorithm not in self.settings.oidc_algorithms
                or header.get("typ") not in self.settings.oidc_token_types
            ):
                raise ValueError
            # Ignore token-supplied jku/x5u. Only configured issuer keys are trusted.
            kid = header.get("kid")
            if not isinstance(kid, str) or not kid or len(kid) > 128:
                raise ValueError
            if self.jwks:
                jwk = self.jwks.get_signing_key_from_jwt(token)
                if jwk.algorithm_name != algorithm:
                    raise ValueError
                key = jwk.key
            else:
                key = self.public_keys[kid]
            claims = jwt.decode(
                token,
                key,
                algorithms=self.settings.oidc_algorithms,
                issuer=self.settings.oidc_issuer,
                audience=self.settings.oidc_audience,
                options={"require": ["iss", "aud", "sub", "exp", "iat"]},
            )
            subject, roles, scope = claims["sub"], claims.get("roles", []), claims.get("scope", "")
            if not isinstance(subject, str) or not 0 < len(subject) <= 256:
                raise ValueError
            if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
                raise ValueError
            if not isinstance(scope, str):
                raise ValueError
            service = claims.get("idtyp") == "app"
            client = claims.get("client_id")
            if service and (not isinstance(client, str) or not 0 < len(client) <= 256):
                raise ValueError
            return Principal(
                subject,
                claims["iss"],
                frozenset(roles),
                frozenset(scope.split()),
                "service" if service else "user",
                client if service else None,
            )
        except (jwt.PyJWTError, ValueError, KeyError, TypeError):
            raise ValueError("Invalid access token") from None


bearer = HTTPBearer(auto_error=False)


async def authenticate(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> Principal:
    await enforce_rate_limit(
        request, "peer:" + (request.client.host if request.client else "unknown")
    )
    try:
        if credentials is None:
            raise ValueError
        principal: Principal = await run_in_threadpool(
            request.app.state.token_validator.validate, credentials.credentials
        )
        request.state.principal = principal
    except ValueError:
        request.app.state.audit.emit(
            "authentication_failure", request_id=getattr(request.state, "request_id", "")
        )
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"}) from None
    await enforce_rate_limit(request, "principal:" + principal.issuer + ":" + principal.subject)
    await run_in_threadpool(
        request.app.state.audit.emit,
        "authentication_success",
        actor=principal.issuer + ":" + principal.subject,
        request_id=getattr(request.state, "request_id", ""),
        outcome="success",
    )
    return principal


async def enforce_rate_limit(request: Request, identity: str) -> None:
    try:
        allowed = await request.app.state.rate_limiter.allow(identity)
    except Exception:
        raise HTTPException(503) from None
    if not allowed:
        request.app.state.audit.emit(
            "rate_limit_denied",
            request_id=getattr(request.state, "request_id", ""),
        )
        raise HTTPException(429, headers={"Retry-After": "60"})


def require_scopes(*scopes: str) -> Any:
    if not scopes or any(scope not in KNOWN_SCOPES for scope in scopes):
        raise ValueError("Unknown or empty authorization scope")

    def authorize(
        request: Request, principal: Annotated[Principal, Depends(authenticate)]
    ) -> Principal:
        if not all(principal.permits(scope) for scope in scopes):
            request.app.state.audit.emit(
                "permission_denied",
                actor=principal.issuer + ":" + principal.subject,
                request_id=getattr(request.state, "request_id", ""),
            )
            raise HTTPException(403)
        return principal

    return Depends(authorize)
