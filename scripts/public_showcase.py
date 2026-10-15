"""Manual collection, private processing, validation and static public publication."""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from aegis.provenance.service import canonical
from aegis.showcase.contracts import SOURCES, parse_export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="one explicit free-source request; no schedule")
    collect.add_argument("--source", choices=tuple(SOURCES), default="nasa")
    collect.add_argument("--limit", type=int, default=20)
    collect.add_argument("--after", type=datetime.fromisoformat)
    collect.add_argument("--before", type=datetime.fromisoformat)
    collect.add_argument("--collection", type=Path, default=Path(".data/showcase/collection.json"))
    export = commands.add_parser(
        "export", help="run existing offline intelligence and sign locally"
    )
    export.add_argument("--collection", type=Path, default=Path(".data/showcase/collection.json"))
    export.add_argument("--output", type=Path, default=Path("apps/showcase/dataset.json"))
    export.add_argument("--key-dir", type=Path, default=Path(".keys/public-showcase"))
    for name in ("validate", "build", "audit"):
        command = commands.add_parser(name)
        command.add_argument("--dataset", type=Path, default=Path("apps/showcase/dataset.json"))
        command.add_argument("--output", type=Path, default=Path("apps/showcase/dist"))
        command.add_argument(
            "--expected-sha256", help="require this exact approved export identity"
        )
    args = parser.parse_args()
    if args.command == "collect":
        from aegis.showcase.collection import collect as acquire
        from aegis.showcase.collection import save_collection

        records = asyncio.run(acquire(args.source, args.limit, args.after, args.before))
        count = save_collection(args.collection, records)
        print(f"Acquired {len(records)} genuine metadata records; {count} unique local records")
    elif args.command == "export":
        from aegis.showcase.collection import export_collection

        result = asyncio.run(export_collection(args.collection, args.output, args.key_dir))
        print(
            f"Validated and signed {len(result.records)} public records; no private bytes exported"
        )
    else:
        from aegis.showcase.site import audit, build, check_trust

        dataset = parse_export(args.dataset.read_bytes())
        check_trust(dataset)
        import hashlib

        digest = hashlib.sha256(canonical(dataset.model_dump(mode="json"))).hexdigest()
        if args.expected_sha256 is not None and args.expected_sha256 != digest:
            raise ValueError("export does not match the explicitly approved SHA-256")
        if args.command == "build":
            build(dataset, args.output)
        elif args.command == "audit":
            audit(dataset, args.output)
        else:
            print(digest)


if __name__ == "__main__":
    main()
