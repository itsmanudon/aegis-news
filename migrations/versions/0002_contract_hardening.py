"""Add explicit canonical document/media associations.

Revision ID: 0002_contract_hardening
Revises: 0001_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_contract_hardening"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_media",
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("media_id", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(16), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("document_id", "media_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"]),
        sa.ForeignKeyConstraint(["media_id"], ["media_assets.media_id"]),
        sa.CheckConstraint("schema_version = '1'", name="document_media_schema_version"),
        sa.CheckConstraint(
            "document_id ~ '^doc_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="document_media_document_id_format",
        ),
        sa.CheckConstraint(
            "media_id ~ '^media_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="document_media_media_id_format",
        ),
    )
    op.create_index("ix_document_media_media_id", "document_media", ["media_id"])


def downgrade() -> None:
    op.drop_index("ix_document_media_media_id", table_name="document_media")
    op.drop_table("document_media")
