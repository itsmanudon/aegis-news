"""A listing maps to one entity: make scheme, identifier and venue unique on their own."""

import sqlalchemy as sa
from alembic import op

revision = "asset_listing_0001"
down_revision = "entity_names_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT scheme, identifier, venue FROM asset_mappings "
                "GROUP BY scheme, identifier, venue HAVING count(*) > 1 "
                "ORDER BY scheme, identifier, venue"
            )
        )
        .all()
    )
    if duplicates:
        # Choosing which entity keeps a listing is a curation decision, not a migration's.
        listed = ", ".join(f"{s}:{i}@{v}" if v else f"{s}:{i}" for s, i, v in duplicates)
        raise RuntimeError(f"Listings mapped to more than one entity; resolve first: {listed}")
    op.create_index(
        "asset_mapping_listing",
        "asset_mappings",
        ["scheme", "identifier", "venue"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.drop_index(
        "asset_mapping_identity", table_name="asset_mappings", postgresql_nulls_not_distinct=True
    )


def downgrade() -> None:
    op.create_index(
        "asset_mapping_identity",
        "asset_mappings",
        ["entity_id", "scheme", "identifier", "venue"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.drop_index(
        "asset_mapping_listing", table_name="asset_mappings", postgresql_nulls_not_distinct=True
    )
