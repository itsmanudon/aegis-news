"""Mint an access token for a machine consumer, offline.

The API never issues tokens. The owner holds an Ed25519 private key, gives the API only
the public half (AEGIS_OIDC_PUBLIC_KEYS), and signs a short-lived token for each
consumer. The token is the same shape the resource server already accepts from an OIDC
issuer for a service principal: idtyp "app", a client_id, and an explicit scope list.
"""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegis.security.auth import KNOWN_SCOPES
from aegis.security.keys import validate_key_id


def mint_service_token(
    signing_key: Ed25519PrivateKey,
    *,
    key_id: str,
    issuer: str,
    audience: str,
    client_id: str,
    scopes: Iterable[str],
    lifetime: timedelta,
    maximum_lifetime: timedelta,
    now: datetime | None = None,
) -> str:
    """Sign a service token. Raises ValueError for anything the API would refuse."""
    validate_key_id(key_id)
    granted = sorted(set(scopes))
    if not granted or any(scope not in KNOWN_SCOPES for scope in granted):
        raise ValueError("Scopes must be a non-empty subset of the known scopes")
    if not issuer or not audience or not 0 < len(client_id) <= 256:
        raise ValueError("Issuer, audience and client id are required")
    if not timedelta(0) < lifetime <= maximum_lifetime:
        raise ValueError("Lifetime must be positive and within the configured maximum")
    issued = now or datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": client_id,
            "iat": issued,
            "exp": issued + lifetime,
            "idtyp": "app",
            "client_id": client_id,
            "scope": " ".join(granted),
        },
        signing_key,
        algorithm="EdDSA",
        headers={"kid": key_id, "typ": "at+jwt"},
    )
