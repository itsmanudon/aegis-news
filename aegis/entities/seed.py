"""Seed curated entities and instrument listings from a JSON file.

    python -m aegis.entities.seed instruments.json [--dry-run]

The file is a JSON array. Each item names one entity and its listings:

    {"name": "Example Industries Limited", "aliases": ["Example Industries"],
     "listings": [{"identifier": "EXAMPLE", "venue": "XNSE"},
                  {"identifier": "500000", "venue": "XBOM"}]}

A listing is an exchange symbol unless it says otherwise, and its venue is an ISO 10383
MIC code. The whole file is validated before anything is written, the write is one
transaction, and running the same file again changes nothing.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from aegis.entities.registry import InstrumentSeed, register
from aegis.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="validate and report, write nothing")
    args = parser.parse_args(argv)
    try:
        seeds = TypeAdapter(list[InstrumentSeed]).validate_python(
            json.loads(args.file.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"seed file rejected: {exc}", file=sys.stderr)
        return 2
    engine = create_engine(get_settings().database_url.get_secret_value())
    try:
        with Session(engine) as session:
            report = register(session, seeds, datetime.now(UTC))
            if args.dry_run:
                session.rollback()
            else:
                session.commit()
        print(json.dumps({"dry_run": args.dry_run, **report.model_dump()}, indent=2))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
