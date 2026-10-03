"""Offline ingestion CLI: python -m aegis.ingestion.cli --help."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegis.domain.ids import new_id
from aegis.domain.models import Source
from aegis.ingestion.importers import historical_requests, local_request
from aegis.ingestion.runtime import make_service
from aegis.ingestion.submissions import TemporalSubmissions
from aegis.settings import get_settings


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    service = make_service(settings)
    try:
        if args.command == "source":
            source = Source.model_validate(
                {
                    "source_id": new_id("src"),
                    "name": args.name,
                    "kind": args.kind,
                    "url": args.url,
                    "created_at": datetime.now(UTC),
                }
            )
            print(service.repository.create_source(source).model_dump_json())
            return
        service.repository.get_source(args.source_id)
        client = TemporalSubmissions(settings)
        if args.command == "local":
            requests = iter(
                [local_request(args.path, args.source_id, args.key, media_paths=args.media)]
            )
        else:
            requests = historical_requests(args.path, args.source_id, args.key)
        for request in requests:
            submission = await client.submit(request)
            if args.wait:
                temporal = await client.connect()
                submission.update(
                    await temporal.get_workflow_handle(
                        submission["workflow_id"],
                    ).result(rpc_timeout=timedelta(minutes=15))
                )
            print(json.dumps(submission, sort_keys=True))
    finally:
        service.repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest bounded offline articles via Temporal")
    commands = parser.add_subparsers(dest="command", required=True)
    source = commands.add_parser("source", help="Create a persistent source")
    source.add_argument("--name", required=True)
    source.add_argument("--kind", choices=["upload", "feed", "api", "web"], default="upload")
    source.add_argument("--url")
    for name in ("local", "historical"):
        command = commands.add_parser(name)
        command.add_argument("path", type=Path)
        command.add_argument("--source-id", required=True)
        command.add_argument("--key", required=True, help="Stable input/dataset namespace")
        command.add_argument("--wait", action="store_true")
        if name == "local":
            command.add_argument("--media", type=Path, action="append", default=[])
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
