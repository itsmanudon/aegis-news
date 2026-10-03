"""Explicit offline JWT fixture issuer. No HTTP login endpoint or password grant."""

from datetime import UTC, datetime, timedelta

import jwt

from aegis.security.auth import ROLE_SCOPES
from aegis.security.keys import FileKeyProvider
from aegis.settings import Settings


def issue_development_token(
    settings: Settings, keys: FileKeyProvider, *, key_id: str, subject: str, role: str
) -> str:
    if (
        settings.environment not in {"development", "test"}
        or not settings.dev_identity_enabled
        or not settings.security_enabled
        or "EdDSA" not in settings.oidc_algorithms
    ):
        raise ValueError("Development identity must be explicitly enabled outside production")
    if role not in ROLE_SCOPES or not 0 < len(subject) <= 256:
        raise ValueError("Invalid development identity")
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": settings.oidc_issuer,
            "aud": settings.oidc_audience,
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "roles": [role],
            "scope": " ".join(sorted(ROLE_SCOPES[role])),
        },
        keys.signing_key(key_id),
        algorithm="EdDSA",
        headers={"kid": key_id, "typ": "at+jwt"},
    )
