"""Withdraw a document from the feed, for example after a publisher takedown.

    python -m aegis.jobs.withdraw DOCUMENT_ID --reason "publisher takedown"

The document moves forward in the feed and is delivered once more as a tombstone: its
``withdrawal`` names the time and reason, and its analyses, entities, instruments and
events are empty, so a consumer deletes what it holds. Withdrawing again changes nothing.
The rows stay in the database and the signed manifests are kept.
"""

import argparse
import json
import sys
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from aegis.persistence.database import make_engine, session_factory
from aegis.persistence.models import DocumentRow, current_xid
from aegis.settings import get_settings


def withdraw(sessions: sessionmaker[Session], document_id: str, reason: str) -> str:
    """Returns "withdrawn", "already_withdrawn", "not_signed" or "not_found"."""
    reason = reason.strip()
    if not 1 <= len(reason) <= 200:
        raise ValueError("reason must be 1 to 200 characters")
    with sessions.begin() as session:
        row = session.get(DocumentRow, document_id, with_for_update=True)
        if row is None:
            return "not_found"
        if row.withdrawn_at is not None:
            return "already_withdrawn"
        if row.last_signed_at is None:
            return "not_signed"
        session.execute(
            update(DocumentRow)
            .where(DocumentRow.document_id == document_id)
            .values(
                withdrawn_at=datetime.now(UTC), withdrawal_reason=reason, signed_xid=current_xid()
            )
        )
    return "withdrawn"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("document_id")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    engine = make_engine(get_settings())
    try:
        outcome = withdraw(session_factory(engine), args.document_id, args.reason)
    except ValueError as exc:
        print(f"withdraw: {exc}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()
    print(json.dumps({args.document_id: outcome}))
    return 0 if outcome in {"withdrawn", "already_withdrawn"} else 1


if __name__ == "__main__":
    sys.exit(main())
