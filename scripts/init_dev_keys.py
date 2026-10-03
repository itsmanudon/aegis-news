"""Initialize a private local Compose key volume; never print key material."""

import os

from aegis.security.keys import generate_development_keys
from aegis.settings import get_settings


def main() -> None:
    settings = get_settings()
    if settings.environment == "production" or not settings.dev_identity_enabled:
        raise ValueError("This initializer is only for explicit local development identity")
    directory, key_id = settings.security_key_directory, settings.provenance_key_id
    if not (directory / f"{key_id}.ed25519.pub").exists():
        generate_development_keys(directory, key_id)
    if hasattr(os, "chown"):
        for path in [directory, *directory.iterdir()]:
            os.chown(path, 10001, 10001)
    print("Local development key volume ready")


if __name__ == "__main__":
    main()
