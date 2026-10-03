"""Private resumability journal for ingestion activities."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "ingestion_0001"
down_revision: str | None = "0002_contract_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_journal",
        sa.Column("ingestion_id", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("metadata_json", JSONB, nullable=False),
        sa.Column("media_json", JSONB, nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("ingestion_id"),
        sa.ForeignKeyConstraint(["ingestion_id"], ["ingestions.ingestion_id"]),
        sa.UniqueConstraint("document_id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_journal")
