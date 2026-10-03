"""Conservative repository secret guard. Reports paths/categories, never secret values."""

import re
import subprocess
from pathlib import Path

PATTERNS = [
    (
        "private key",
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?" + rb"PRIVATE KEY-----"),
    ),
    ("access token", re.compile(rb"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}")),
    ("AWS access key", re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}")),
    ("GitHub token", re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}")),
]


def violations(path: str, content: bytes) -> list[str]:
    result = [label for label, pattern in PATTERNS if pattern.search(content)]
    name = Path(path).name
    if name.endswith((".pem", ".key", ".pfx", ".p12", ".jwk", ".sqlite3")) or (
        name.startswith(".env") and name != ".env.example"
    ):
        result.append("forbidden secret file")
    return result


def main() -> None:
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
        )
        .decode()
        .split("\0")
    )
    failures = []
    for path in filter(None, paths):
        file = Path(path)
        if file.is_file():
            for category in violations(path, file.read_bytes()):
                failures.append(f"{path}: {category}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Repository secret guard passed")


if __name__ == "__main__":
    main()
