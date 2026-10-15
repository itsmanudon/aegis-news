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
    key = commands.add_parser(
        "daily-key", help="explicitly provision a separate unattended signing key locally"
    )
    key.add_argument("--key-file", type=Path, default=Path(".keys/daily-publication/daily-v1.key"))
    key.add_argument("--key-id", default="daily-v1")
    daily = commands.add_parser(
        "daily", help="one bounded multi-source acquisition and signed release"
    )
    daily.add_argument("--previous", type=Path, default=Path("apps/showcase/dataset.json"))
    daily.add_argument("--output", type=Path, default=Path(".data/daily/candidate.json"))
    daily.add_argument("--key-file", type=Path)
    daily.add_argument("--report", type=Path, default=Path(".data/daily/report.json"))
    for name in ("state-bootstrap", "state-read", "state-stage", "state-promote", "state-release"):
        state = commands.add_parser(name)
        state.add_argument("--dataset", type=Path, default=Path("apps/showcase/dataset.json"))
        state.add_argument("--output", type=Path, default=Path(".data/daily/previous.json"))
        state.add_argument("--candidate", type=Path, default=Path(".data/daily/candidate.json"))
        state.add_argument("--expected-head")
        state.add_argument("--release")
        state.add_argument("--preview", action="store_true")
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
    if args.command == "daily-key":
        from aegis.showcase.daily import initialize_key

        initialize_key(args.key_file, args.key_id)
    elif args.command == "daily":
        from aegis.showcase.daily import run

        published = asyncio.run(run(args.previous, args.output, args.key_file, args.report))
        print("Validated daily candidate prepared" if published else "No publication changes")
    elif args.command.startswith("state-"):
        import json

        from aegis.showcase.contracts import DailyExport
        from aegis.showcase.state import GitHubState

        state_store = GitHubState()
        if args.command == "state-bootstrap":
            print(state_store.bootstrap(parse_export(args.dataset.read_bytes())))
        elif args.command == "state-read":
            state_result = state_store.download(args.output, args.candidate)
            print(json.dumps(state_result))
        elif args.command == "state-release":
            release = state_store.release(args.release or "")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical(release.model_dump(mode="json")))
        elif args.command == "state-stage":
            staged_export = parse_export(args.dataset.read_bytes())
            if not isinstance(staged_export, DailyExport) or not args.expected_head:
                raise ValueError("staging requires a signed daily release and exact state head")
            print(state_store.prepare(staged_export, args.expected_head, preview=args.preview))
        else:
            if not args.expected_head or not args.release:
                raise ValueError("promotion requires exact head and release")
            print(state_store.promote(args.release, args.expected_head))
    elif args.command == "collect":
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
