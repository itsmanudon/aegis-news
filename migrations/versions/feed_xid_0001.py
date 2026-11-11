"""Order the feed by signing transaction, so a late commit is delayed, never skipped."""

import sqlalchemy as sa
from alembic import op

revision = "feed_xid_0001"
down_revision = "provider_usage_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("signed_xid", sa.BigInteger()))
    # Every signed document so far gets this migration's id; the feed breaks the tie by
    # document id. Their signing transactions have all finished.
    op.execute(
        "UPDATE documents SET signed_xid = pg_current_xact_id()::text::bigint "
        "WHERE last_signed_at IS NOT NULL"
    )
    op.create_check_constraint(
        "document_signed_xid", "documents", "(signed_xid IS NULL) = (last_signed_at IS NULL)"
    )
    op.create_index("document_feed_xid", "documents", ["signed_xid", "document_id"])


def downgrade() -> None:
    op.drop_index("document_feed_xid", table_name="documents")
    op.drop_constraint("document_signed_xid", "documents", type_="check")
    op.drop_column("documents", "signed_xid")
