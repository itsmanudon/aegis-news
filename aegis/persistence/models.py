"""Foundation storage schema. Domain/API models remain independent of the ORM."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Versioned:
    schema_version: Mapped[str] = mapped_column(String(16), default="1", server_default="1")


class SourceRow(Versioned, Base):
    __tablename__ = "sources"
    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(32))
    url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RawObjectRow(Versioned, Base):
    __tablename__ = "raw_objects"
    raw_object_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(512))
    key: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="raw_object_size"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="raw_object_hash"),
        UniqueConstraint("bucket", "key", name="raw_object_location"),
    )


class IngestionRow(Versioned, Base):
    __tablename__ = "ingestions"
    ingestion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), index=True)
    raw_object_id: Mapped[str] = mapped_column(ForeignKey("raw_objects.raw_object_id"))
    source_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(512))
    __table_args__ = (
        UniqueConstraint("source_id", "idempotency_key", name="ingestion_dedup"),
        CheckConstraint("ingested_at >= first_seen_at", name="ingestion_time_order"),
    )


class DocumentRow(Versioned, Base):
    __tablename__ = "documents"
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("ingestions.ingestion_id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(35))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = (
        CheckConstraint("revision >= 1", name="document_revision"),
        CheckConstraint(
            "ingested_at >= first_seen_at AND created_at >= ingested_at", name="document_time_order"
        ),
    )


class MediaAssetRow(Versioned, Base):
    __tablename__ = "media_assets"
    media_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("ingestions.ingestion_id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    raw_object_id: Mapped[str] = mapped_column(ForeignKey("raw_objects.raw_object_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EntityRow(Versioned, Base):
    __tablename__ = "entities"
    entity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AnalysisRow(Versioned, Base):
    __tablename__ = "analyses"
    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), index=True)
    analysis_type: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(512))
    model_name: Mapped[str] = mapped_column(String(512))
    model_version: Mapped[str] = mapped_column(String(512))
    configuration_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    outputs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    __table_args__ = (
        CheckConstraint("available_at >= created_at", name="analysis_time_order"),
        CheckConstraint(
            "configuration_hash ~ '^[0-9a-f]{64}$'", name="analysis_configuration_hash"
        ),
        CheckConstraint(
            "jsonb_typeof(outputs) = 'array' AND jsonb_array_length(outputs) > 0",
            name="analysis_outputs",
        ),
    )


class EntityMentionRow(Versioned, Base):
    __tablename__ = "entity_mentions"
    mention_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), index=True)
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.entity_id"), index=True)
    surface: Mapped[str] = mapped_column(String(512))
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    evidence_kind: Mapped[str] = mapped_column(String(32))
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.analysis_id"))
    __table_args__ = (
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="mention_span"),
        CheckConstraint(
            "(evidence_kind = 'fact' AND analysis_id IS NULL) OR "
            "(evidence_kind = 'model_output' AND analysis_id IS NOT NULL)",
            name="mention_evidence",
        ),
    )


class AssetMappingRow(Versioned, Base):
    __tablename__ = "asset_mappings"
    mapping_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.entity_id"), index=True)
    scheme: Mapped[str] = mapped_column(String(32))
    identifier: Mapped[str] = mapped_column(String(512))
    venue: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "scheme <> 'exchange_symbol' OR venue IS NOT NULL", name="asset_mapping_venue"
        ),
        Index(
            "asset_mapping_identity",
            "entity_id",
            "scheme",
            "identifier",
            "venue",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )


class NewsEventRow(Versioned, Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary: Mapped[str] = mapped_column(String(512))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_kind: Mapped[str] = mapped_column(String(32))
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.analysis_id"))
    __table_args__ = (
        CheckConstraint("revision >= 1", name="event_revision"),
        CheckConstraint("available_at >= created_at", name="event_time_order"),
        CheckConstraint(
            "(evidence_kind = 'fact' AND analysis_id IS NULL) OR "
            "(evidence_kind = 'model_output' AND analysis_id IS NOT NULL)",
            name="event_evidence",
        ),
    )


class ProvenanceRow(Versioned, Base):
    __tablename__ = "provenance_records"
    provenance_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(512), index=True)
    input_ids: Mapped[list[str]] = mapped_column(JSONB)
    operation: Mapped[str] = mapped_column(String(512))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64))
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.analysis_id"))
    __table_args__ = (CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="provenance_hash"),)


class OutboxRow(Base):
    __tablename__ = "outbox_events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(512))
    event_version: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    producer: Mapped[str] = mapped_column(String(512))
    correlation_id: Mapped[str] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(512))
    envelope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    __table_args__ = (
        UniqueConstraint("producer", "event_type", "idempotency_key", name="outbox_dedup"),
        CheckConstraint("attempts >= 0", name="outbox_attempts"),
        Index("outbox_pending", "created_at", postgresql_where=text("dispatched_at IS NULL")),
    )


for name, column, target in (
    ("event_entities", "entity_id", "entities.entity_id"),
    ("event_documents", "document_id", "documents.document_id"),
):
    Table(
        name,
        Base.metadata,
        Column("event_id", String(64), primary_key=True),
        Column("revision", Integer, primary_key=True),
        Column(column, String(64), ForeignKey(target), primary_key=True),
        ForeignKeyConstraint(["event_id", "revision"], ["events.event_id", "events.revision"]),
    )

# Canonical wire identifier and version validation also applies to direct SQL writers.
ID_PREFIXES = {
    "source_id": "src",
    "raw_object_id": "raw",
    "ingestion_id": "ing",
    "document_id": "doc",
    "media_id": "media",
    "entity_id": "ent",
    "analysis_id": "ana",
    "mention_id": "mention",
    "mapping_id": "map",
    "provenance_id": "prov",
}
for table in Base.metadata.tables.values():
    for key_column in table.primary_key.columns:
        prefix = "msg" if table.name == "outbox_events" else ID_PREFIXES.get(key_column.name)
        if key_column.name == "event_id" and table.name != "outbox_events":
            prefix = "evt"
        if prefix:
            pattern = (
                f"^{prefix}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$"
            )
            table.append_constraint(
                CheckConstraint(
                    f"{key_column.name} ~ '{pattern}'",
                    name=f"{table.name}_{key_column.name}_format",
                )
            )
    if "schema_version" in table.c:
        table.append_constraint(
            CheckConstraint("schema_version = '1'", name=f"{table.name}_schema_version")
        )
