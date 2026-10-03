"""Security audit and signed manifests, branching from frozen hardening revision."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "security_0001"
down_revision = "0002_contract_hardening"
branch_labels = ("security",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_hash", sa.String(64)),
        sa.Column("subject_hash", sa.String(64)),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_table(
        "signed_manifests",
        sa.Column("manifest_hash", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("key_id", sa.String(64), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
    )
    op.execute("""CREATE FUNCTION aegis_security_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'security records are append-only'; END; $$""")
    for table in ("audit_events", "signed_manifests"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION aegis_security_append_only()"
        )


def downgrade() -> None:
    op.drop_table("signed_manifests")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.execute("DROP FUNCTION aegis_security_append_only()")
