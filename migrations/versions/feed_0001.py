"""Document availability stamps for the incremental feed."""

import sqlalchemy as sa
from alembic import op

revision = "feed_0001"
down_revision = "live_providers_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("available_at", sa.DateTime(timezone=True)))
    op.add_column("documents", sa.Column("last_signed_at", sa.DateTime(timezone=True)))
    # Documents signed before this revision take their stamps from the manifests that
    # already cover them. A manifest records the document as its normalization subject.
    # GREATEST guards the time-order constraint against a manifest clock that ran behind.
    op.execute(
        """
        UPDATE documents d
        SET available_at = GREATEST(m.first_signed, d.created_at),
            last_signed_at = GREATEST(m.last_signed, d.created_at)
        FROM (
            SELECT r->>'subject_id' AS document_id,
                   MIN(s.created_at) AS first_signed,
                   MAX(s.created_at) AS last_signed
            FROM signed_manifests s
            CROSS JOIN LATERAL jsonb_array_elements(s.manifest->'records') r
            WHERE r->>'operation' = 'normalization'
            GROUP BY 1
        ) m
        WHERE d.document_id = m.document_id
        """
    )
    op.create_check_constraint(
        "document_availability",
        "documents",
        "(available_at IS NULL) = (last_signed_at IS NULL) AND "
        "(available_at IS NULL OR "
        "(available_at >= created_at AND last_signed_at >= available_at))",
    )
    op.create_index("document_feed_position", "documents", ["last_signed_at", "document_id"])
    op.create_index("ix_signed_manifests_created_at", "signed_manifests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_signed_manifests_created_at", table_name="signed_manifests")
    op.drop_index("document_feed_position", table_name="documents")
    op.drop_constraint("document_availability", "documents", type_="check")
    op.drop_column("documents", "last_signed_at")
    op.drop_column("documents", "available_at")
