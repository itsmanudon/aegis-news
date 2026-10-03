"""Security-only persistence; append-only PostgreSQL triggers are in security_0001."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, insert, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from aegis.persistence.models import Base
from aegis.security.audit import AuditEvent


class AuditEventRow(Base):
    __tablename__ = "audit_events"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    action: Mapped[str] = mapped_column(String(64))
    actor_hash: Mapped[str | None] = mapped_column(String(64))
    subject_hash: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(16))


class SignedManifestRow(Base):
    __tablename__ = "signed_manifests"
    manifest_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))


class SQLAuditSink:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def append(self, event: AuditEvent) -> None:
        with self.engine.begin() as connection:
            connection.execute(insert(AuditEventRow).values(**event.model_dump()))

    def recent(self, limit: int) -> tuple[AuditEvent, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(AuditEventRow.__table__)
                .order_by(AuditEventRow.occurred_at.desc(), AuditEventRow.event_id.desc())
                .limit(max(1, min(limit, 100)))
            )
            return tuple(AuditEvent.model_validate(dict(row)) for row in rows.mappings())


class SQLManifestStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def append(
        self, manifest_hash: str, manifest: dict[str, Any], key_id: str, created_at: datetime
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(SignedManifestRow).values(
                    manifest_hash=manifest_hash,
                    manifest=manifest,
                    key_id=key_id,
                    created_at=created_at,
                )
            )
