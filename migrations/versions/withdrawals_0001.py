"""Withdrawn documents: a stamp and a reason, so the feed can send a tombstone."""

import sqlalchemy as sa
from alembic import op

revision = "withdrawals_0001"
down_revision = "feed_xid_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("withdrawn_at", sa.DateTime(timezone=True)))
    op.add_column("documents", sa.Column("withdrawal_reason", sa.String(200)))
    op.create_check_constraint(
        "document_withdrawal",
        "documents",
        "(withdrawn_at IS NULL) = (withdrawal_reason IS NULL) AND "
        "(withdrawn_at IS NULL OR last_signed_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("document_withdrawal", "documents", type_="check")
    op.drop_column("documents", "withdrawal_reason")
    op.drop_column("documents", "withdrawn_at")
