"""Generate ignored development keys or print a five-minute offline demo JWT."""

import argparse

from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider, generate_development_keys
from aegis.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "token"])
    parser.add_argument("--key-id", default="dev")
    parser.add_argument("--role", default="analyst")
    parser.add_argument("--subject", default="synthetic-demo")
    args = parser.parse_args()
    settings = get_settings()
    if settings.environment == "production":
        parser.error("Development tooling is disabled in production")
    if args.command == "generate":
        generate_development_keys(settings.security_key_directory, args.key_id)
        print("Development keys created. Restrict directory ACLs; do not commit or share.")
    else:
        print(
            issue_development_token(
                settings,
                FileKeyProvider(settings.security_key_directory),
                key_id=args.key_id,
                subject=args.subject,
                role=args.role,
            )
        )


if __name__ == "__main__":
    main()
