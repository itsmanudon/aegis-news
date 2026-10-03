"""Join independent ingestion and security migrations without rebasing either."""

revision = "mvp_merge_0001"
down_revision = ("ingestion_0001", "security_0001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
