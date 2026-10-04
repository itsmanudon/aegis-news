"""Acquisition evidence and expiring external references, no canonical model changes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "live_providers_0001"
down_revision = "mvp_merge_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_articles",
        sa.Column("article_id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id"), nullable=False),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("documents.document_id")),
        sa.Column("workflow_id", sa.String(128)),
        sa.Column("request", JSONB, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("document_id", "workflow_id", "acquired_at"):
        op.create_index("ix_provider_articles_" + column, "provider_articles", [column])
    op.create_table(
        "provider_article_aliases",
        sa.Column("alias_key", sa.String(128), primary_key=True),
        sa.Column(
            "article_id",
            sa.String(36),
            sa.ForeignKey("provider_articles.article_id"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_provider_article_aliases_article_id", "provider_article_aliases", ["article_id"]
    )
    op.create_table(
        "provider_evidence",
        sa.Column("evidence_key", sa.String(128), primary_key=True),
        sa.Column(
            "article_id",
            sa.String(36),
            sa.ForeignKey("provider_articles.article_id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("metadata_value", JSONB, nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_evidence_article_id", "provider_evidence", ["article_id"])
    op.create_table(
        "provider_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("report", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_runs_created_at", "provider_runs", ["created_at"])
    op.create_table(
        "youtube_references",
        sa.Column("video_id", sa.String(11), primary_key=True),
        sa.Column("metadata_value", JSONB, nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_youtube_references_expires_at", "youtube_references", ["expires_at"])


def downgrade() -> None:
    for table in (
        "youtube_references",
        "provider_runs",
        "provider_evidence",
        "provider_article_aliases",
        "provider_articles",
    ):
        op.drop_table(table)
