"""Create a service signing key, or mint a short-lived service token with it.

Run this on the owner's machine, never on the API host. The private key stays where it
was generated; the API is given the public key only.

    uv run python -m scripts.service_token generate --key-id stockviz-2026 --directory ~/aegis-keys
    uv run python -m scripts.service_token mint --key-file ~/aegis-keys/stockviz-2026.ed25519.key \\
        --key-id stockviz-2026 --issuer https://example.org/aegis --audience aegisnews \\
        --client-id stockviz-sync --scope feed:read --minutes 15

`generate` prints the AEGIS_OIDC_PUBLIC_KEYS value to set on the API. `mint` prints the
token and nothing else, so it can be captured by a job; do not paste it into a file or a
log. Issuer and audience must equal the API's AEGIS_OIDC_ISSUER and AEGIS_OIDC_AUDIENCE.
"""

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegis.security.keys import generate_signing_keys
from aegis.security.service_token import mint_service_token
from aegis.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="write a new Ed25519 key pair")
    generate.add_argument("--key-id", required=True)
    generate.add_argument("--directory", required=True, type=Path)
    mint = commands.add_parser("mint", help="print a signed service token")
    mint.add_argument("--key-file", required=True, type=Path)
    mint.add_argument("--key-id", required=True)
    mint.add_argument("--issuer", required=True)
    mint.add_argument("--audience", required=True)
    mint.add_argument("--client-id", required=True)
    mint.add_argument("--scope", action="append", required=True, help="repeat for each scope")
    mint.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            private, public = generate_signing_keys(args.directory.expanduser(), args.key_id)
            print(f"Private key: {private}  (keep it off the API host and out of Git)")
            print("Set on the API, merged with any keys already there:")
            print("AEGIS_OIDC_PUBLIC_KEYS=" + json.dumps({args.key_id: public.read_text()}))
            print('AEGIS_OIDC_ALGORITHMS=["EdDSA"]')
            return 0
        key = serialization.load_pem_private_key(
            args.key_file.expanduser().read_bytes(), password=None
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Ed25519 private key required")
        print(
            mint_service_token(
                key,
                key_id=args.key_id,
                issuer=args.issuer,
                audience=args.audience,
                client_id=args.client_id,
                scopes=args.scope,
                lifetime=timedelta(minutes=args.minutes),
                maximum_lifetime=timedelta(seconds=get_settings().oidc_max_token_lifetime),
            )
        )
        return 0
    except (OSError, ValueError) as error:
        # Never echo key material or a token: the message names the problem only.
        print(f"service_token: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
