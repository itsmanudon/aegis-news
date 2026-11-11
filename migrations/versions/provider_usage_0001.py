"""Requests per provider per UTC day, so a provider budget holds across runs."""

import sqlalchemy as sa
from alembic import op

revision = "provider_usage_0001"
down_revision = "asset_listing_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_daily_usage",
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.Column("exhausted_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("provider_daily_usage")
