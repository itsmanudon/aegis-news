"""create canonical foundation and outbox

Revision ID: 0001_foundation
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "entities",
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_name", sa.String(length=512), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "entity_id ~ '^ent_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="entities_entity_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="entities_schema_version"),
        sa.PrimaryKeyConstraint("entity_id"),
    )
    op.create_table(
        "outbox_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=512), nullable=False),
        sa.Column("event_version", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("producer", sa.String(length=512), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "event_id ~ '^msg_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="outbox_events_event_id_format",
        ),
        sa.CheckConstraint("attempts >= 0", name="outbox_attempts"),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("producer", "event_type", "idempotency_key", name="outbox_dedup"),
    )
    op.create_index(
        "outbox_pending",
        "outbox_events",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("dispatched_at IS NULL"),
    )
    op.create_table(
        "raw_objects",
        sa.Column("raw_object_id", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.String(length=512), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "raw_object_id ~ '^raw_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="raw_objects_raw_object_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="raw_objects_schema_version"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="raw_object_hash"),
        sa.CheckConstraint("size_bytes >= 0", name="raw_object_size"),
        sa.PrimaryKeyConstraint("raw_object_id"),
        sa.UniqueConstraint("bucket", "key", name="raw_object_location"),
    )
    op.create_table(
        "sources",
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint("schema_version = '1'", name="sources_schema_version"),
        sa.CheckConstraint(
            "source_id ~ '^src_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="sources_source_id_format",
        ),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_table(
        "asset_mappings",
        sa.Column("mapping_id", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("scheme", sa.String(length=32), nullable=False),
        sa.Column("identifier", sa.String(length=512), nullable=False),
        sa.Column("venue", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "mapping_id ~ '^map_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="asset_mappings_mapping_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="asset_mappings_schema_version"),
        sa.CheckConstraint(
            "scheme <> 'exchange_symbol' OR venue IS NOT NULL", name="asset_mapping_venue"
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.entity_id"],
        ),
        sa.PrimaryKeyConstraint("mapping_id"),
    )
    op.create_index(
        "asset_mapping_identity",
        "asset_mappings",
        ["entity_id", "scheme", "identifier", "venue"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        op.f("ix_asset_mappings_entity_id"), "asset_mappings", ["entity_id"], unique=False
    )
    op.create_table(
        "ingestions",
        sa.Column("ingestion_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("raw_object_id", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "ingestion_id ~ '^ing_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="ingestions_ingestion_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="ingestions_schema_version"),
        sa.CheckConstraint("ingested_at >= first_seen_at", name="ingestion_time_order"),
        sa.ForeignKeyConstraint(
            ["raw_object_id"],
            ["raw_objects.raw_object_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
        ),
        sa.PrimaryKeyConstraint("ingestion_id"),
        sa.UniqueConstraint("source_id", "idempotency_key", name="ingestion_dedup"),
    )
    op.create_index(op.f("ix_ingestions_source_id"), "ingestions", ["source_id"], unique=False)
    op.create_table(
        "documents",
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("ingestion_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=35), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "document_id ~ '^doc_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="documents_document_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="documents_schema_version"),
        sa.CheckConstraint(
            "ingested_at >= first_seen_at AND created_at >= ingested_at", name="document_time_order"
        ),
        sa.CheckConstraint("revision >= 1", name="document_revision"),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.ingestion_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(op.f("ix_documents_ingestion_id"), "documents", ["ingestion_id"], unique=False)
    op.create_index(op.f("ix_documents_source_id"), "documents", ["source_id"], unique=False)
    op.create_table(
        "media_assets",
        sa.Column("media_id", sa.String(length=64), nullable=False),
        sa.Column("ingestion_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("raw_object_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "media_id ~ '^media_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="media_assets_media_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="media_assets_schema_version"),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.ingestion_id"],
        ),
        sa.ForeignKeyConstraint(
            ["raw_object_id"],
            ["raw_objects.raw_object_id"],
        ),
        sa.PrimaryKeyConstraint("media_id"),
    )
    op.create_index(
        op.f("ix_media_assets_ingestion_id"), "media_assets", ["ingestion_id"], unique=False
    )
    op.create_table(
        "analyses",
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=512), nullable=False),
        sa.Column("model_name", sa.String(length=512), nullable=False),
        sa.Column("model_version", sa.String(length=512), nullable=False),
        sa.Column("configuration_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "analysis_id ~ '^ana_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="analyses_analysis_id_format",
        ),
        sa.CheckConstraint(
            "configuration_hash ~ '^[0-9a-f]{64}$'", name="analysis_configuration_hash"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(outputs) = 'array' AND jsonb_array_length(outputs) > 0",
            name="analysis_outputs",
        ),
        sa.CheckConstraint("schema_version = '1'", name="analyses_schema_version"),
        sa.CheckConstraint("available_at >= created_at", name="analysis_time_order"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
        ),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    op.create_index(op.f("ix_analyses_available_at"), "analyses", ["available_at"], unique=False)
    op.create_index(op.f("ix_analyses_document_id"), "analyses", ["document_id"], unique=False)
    op.create_table(
        "entity_mentions",
        sa.Column("mention_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("surface", sa.String(length=512), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("evidence_kind", sa.String(length=32), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "(evidence_kind = 'fact' AND analysis_id IS NULL) OR "
            "(evidence_kind = 'model_output' AND analysis_id IS NOT NULL)",
            name="mention_evidence",
        ),
        sa.CheckConstraint(
            "mention_id ~ '^mention_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="entity_mentions_mention_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="entity_mentions_schema_version"),
        sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="mention_span"),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.analysis_id"],
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.entity_id"],
        ),
        sa.PrimaryKeyConstraint("mention_id"),
    )
    op.create_index(
        op.f("ix_entity_mentions_document_id"), "entity_mentions", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_entity_mentions_entity_id"), "entity_mentions", ["entity_id"], unique=False
    )
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_kind", sa.String(length=32), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint(
            "(evidence_kind = 'fact' AND analysis_id IS NULL) OR "
            "(evidence_kind = 'model_output' AND analysis_id IS NOT NULL)",
            name="event_evidence",
        ),
        sa.CheckConstraint(
            "event_id ~ '^evt_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="events_event_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="events_schema_version"),
        sa.CheckConstraint("available_at >= created_at", name="event_time_order"),
        sa.CheckConstraint("revision >= 1", name="event_revision"),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.analysis_id"],
        ),
        sa.PrimaryKeyConstraint("event_id", "revision"),
    )
    op.create_index(op.f("ix_events_available_at"), "events", ["available_at"], unique=False)
    op.create_table(
        "provenance_records",
        sa.Column("provenance_id", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=512), nullable=False),
        sa.Column("input_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("operation", sa.String(length=512), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=16), server_default="1", nullable=False),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="provenance_hash"),
        sa.CheckConstraint(
            "provenance_id ~ '^prov_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="provenance_records_provenance_id_format",
        ),
        sa.CheckConstraint("schema_version = '1'", name="provenance_records_schema_version"),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.analysis_id"],
        ),
        sa.PrimaryKeyConstraint("provenance_id"),
    )
    op.create_index(
        op.f("ix_provenance_records_subject_id"), "provenance_records", ["subject_id"], unique=False
    )
    op.create_table(
        "event_documents",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "document_id ~ '^doc_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="event_documents_document_id_format",
        ),
        sa.CheckConstraint(
            "event_id ~ '^evt_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="event_documents_event_id_format",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "revision"],
            ["events.event_id", "events.revision"],
        ),
        sa.PrimaryKeyConstraint("event_id", "revision", "document_id"),
    )
    op.create_table(
        "event_entities",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "entity_id ~ '^ent_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="event_entities_entity_id_format",
        ),
        sa.CheckConstraint(
            "event_id ~ '^evt_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="event_entities_event_id_format",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.entity_id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "revision"],
            ["events.event_id", "events.revision"],
        ),
        sa.PrimaryKeyConstraint("event_id", "revision", "entity_id"),
    )
    op.execute("""
        CREATE FUNCTION aegis_reject_analysis_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'analysis records are immutable; insert a new analysis_id'
                USING ERRCODE = '55000';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER analyses_append_only
        BEFORE UPDATE OR DELETE ON analyses
        FOR EACH ROW EXECUTE FUNCTION aegis_reject_analysis_mutation()
    """)
    op.execute("""
        CREATE TRIGGER analyses_no_truncate
        BEFORE TRUNCATE ON analyses
        FOR EACH STATEMENT EXECUTE FUNCTION aegis_reject_analysis_mutation()
    """)


def downgrade() -> None:
    # Destructive reversal is only intended for explicitly owned local scratch databases.
    op.execute("DROP TRIGGER analyses_no_truncate ON analyses")
    op.execute("DROP TRIGGER analyses_append_only ON analyses")
    op.execute("DROP FUNCTION aegis_reject_analysis_mutation()")

    op.drop_table("event_entities")
    op.drop_table("event_documents")
    op.drop_index(op.f("ix_provenance_records_subject_id"), table_name="provenance_records")
    op.drop_table("provenance_records")
    op.drop_index(op.f("ix_events_available_at"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_entity_mentions_entity_id"), table_name="entity_mentions")
    op.drop_index(op.f("ix_entity_mentions_document_id"), table_name="entity_mentions")
    op.drop_table("entity_mentions")
    op.drop_index(op.f("ix_analyses_document_id"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_available_at"), table_name="analyses")
    op.drop_table("analyses")
    op.drop_index(op.f("ix_media_assets_ingestion_id"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index(op.f("ix_documents_source_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_ingestion_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_ingestions_source_id"), table_name="ingestions")
    op.drop_table("ingestions")
    op.drop_index(op.f("ix_asset_mappings_entity_id"), table_name="asset_mappings")
    op.drop_index(
        "asset_mapping_identity", table_name="asset_mappings", postgresql_nulls_not_distinct=True
    )
    op.drop_table("asset_mappings")
    op.drop_table("sources")
    op.drop_table("raw_objects")
    op.drop_index(
        "outbox_pending",
        table_name="outbox_events",
        postgresql_where=sa.text("dispatched_at IS NULL"),
    )
    op.drop_table("outbox_events")
    op.drop_table("entities")
    # Extensions may be shared; retain them on downgrade.
