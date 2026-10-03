"""Ingestion persistence adapter. All canonical completion writes share one transaction."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ForeignKey, String, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from aegis.contracts.events import DocumentIngestedEvent, DocumentNormalizedEvent
from aegis.domain.ids import new_id
from aegis.domain.models import NewsDocument, ObjectReference, RawIngestion, Source
from aegis.events.outbox import stage_event
from aegis.ingestion.inputs import IngestionRequest
from aegis.persistence.models import (
    Base,
    DocumentMediaLinkRow,
    DocumentRow,
    IngestionRow,
    MediaAssetRow,
    RawObjectRow,
    SourceRow,
)


class IngestionJournalRow(Base):
    """Private resumability state, not a new canonical domain contract."""

    __tablename__ = "ingestion_journal"
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.ingestion_id"), primary_key=True
    )
    request_digest: Mapped[str] = mapped_column(String(64))
    document_id: Mapped[str] = mapped_column(String(64), unique=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    media_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    correlation_id: Mapped[str] = mapped_column(String(128))


def source_value(row: SourceRow) -> Source:
    return Source.model_validate({k: getattr(row, k) for k in Source.model_fields})


def document_value(row: DocumentRow) -> NewsDocument:
    return NewsDocument.model_validate({k: getattr(row, k) for k in NewsDocument.model_fields})


def object_value(row: RawObjectRow) -> ObjectReference:
    return ObjectReference.model_validate(
        {k: getattr(row, k) for k in ObjectReference.model_fields}
    )


def ingestion_value(session: Session, row: IngestionRow) -> RawIngestion:
    obj = session.get(RawObjectRow, row.raw_object_id)
    if obj is None:
        raise LookupError("raw object not found")
    return RawIngestion.model_validate(
        {
            **{k: getattr(row, k) for k in RawIngestion.model_fields if k != "object"},
            "object": object_value(obj),
        }
    )


class IngestionRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def close(self) -> None:
        bind = self.sessions.kw.get("bind")
        if isinstance(bind, Engine):
            bind.dispose()

    def create_source(self, source: Source) -> Source:
        with self.sessions.begin() as session:
            existing = session.get(SourceRow, source.source_id)
            if existing:
                if source_value(existing) != source:
                    raise ValueError("source already exists with different metadata")
                return source_value(existing)
            session.add(
                SourceRow(
                    **source.model_dump(mode="json", exclude={"created_at"}),
                    created_at=source.created_at,
                )
            )
        return source

    def get_source(self, source_id: str) -> Source:
        with self.sessions() as session:
            row = session.get(SourceRow, source_id)
            if row is None:
                raise LookupError("source not found")
            return source_value(row)

    def get_document(self, document_id: str) -> NewsDocument:
        with self.sessions() as session:
            row = session.get(DocumentRow, document_id)
            if row is None:
                raise LookupError("document not found")
            return document_value(row)

    def get_ingestion(self, ingestion_id: str) -> RawIngestion:
        with self.sessions() as session:
            row = session.get(IngestionRow, ingestion_id)
            if row is None:
                raise LookupError("ingestion not found")
            return ingestion_value(session, row)

    def find_retry(self, source_id: str, key: str, digest: str) -> str | None:
        with self.sessions() as session:
            row = session.scalar(
                select(IngestionRow).where(
                    IngestionRow.source_id == source_id,
                    IngestionRow.idempotency_key == key,
                )
            )
            if row is None:
                return None
            journal = session.get(IngestionJournalRow, row.ingestion_id)
            if journal is None or journal.request_digest != digest:
                raise ValueError("idempotency key reused with different request")
            return row.ingestion_id

    @staticmethod
    def lock(session: Session, identity: str) -> None:
        lock_id = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": lock_id})

    @staticmethod
    def persist_object(session: Session, ref: ObjectReference, now: datetime) -> str:
        # Shared locations serialize independently of source/key ingestion locks.
        IngestionRepository.lock(session, f"object:{ref.bucket}:{ref.key}")
        row = session.scalar(
            select(RawObjectRow).where(
                RawObjectRow.bucket == ref.bucket,
                RawObjectRow.key == ref.key,
            )
        )
        if row:
            if object_value(row) != ref:
                raise ValueError("object reference integrity conflict")
            return row.raw_object_id
        raw_id = new_id("raw")
        session.add(RawObjectRow(raw_object_id=raw_id, created_at=now, **ref.model_dump()))
        session.flush()
        return raw_id

    def persist_ingestion(
        self,
        request: IngestionRequest,
        digest: str,
        raw: ObjectReference,
        media: list[dict[str, Any]],
        published_at: datetime | None,
        observed_at: datetime,
    ) -> str:
        with self.sessions.begin() as session:
            self.lock(session, f"ingestion:{request.source_id}:{request.idempotency_key}")
            existing = session.scalar(
                select(IngestionRow).where(
                    IngestionRow.source_id == request.source_id,
                    IngestionRow.idempotency_key == request.idempotency_key,
                )
            )
            if existing:
                journal = session.get(IngestionJournalRow, existing.ingestion_id)
                if journal is None or journal.request_digest != digest:
                    raise ValueError("idempotency key reused with different request")
                return existing.ingestion_id
            now = datetime.now(UTC)
            first_seen = request.first_seen_at or observed_at
            if first_seen > now:
                raise ValueError("first_seen_at is in the future")
            raw_id = self.persist_object(session, raw, now)
            # Sort object lock acquisition so shared media cannot deadlock across ingestions.
            refs = [ObjectReference.model_validate(m["object"]) for m in media]
            media_objects = {
                ref.key: self.persist_object(session, ref, now)
                for ref in sorted(refs, key=lambda r: r.key)
            }
            ingestion_id = new_id("ing")
            ingestion = RawIngestion(
                ingestion_id=ingestion_id,
                source_id=request.source_id,
                raw_object_id=raw_id,
                object=raw,
                source_url=request.source_url,
                published_at=published_at,
                first_seen_at=first_seen,
                ingested_at=now,
                idempotency_key=request.idempotency_key,
            )
            data = ingestion.model_dump(exclude={"object", "source_url"})
            session.add(
                IngestionRow(
                    **data, source_url=str(request.source_url) if request.source_url else None
                )
            )
            session.flush()
            session.add(
                IngestionJournalRow(
                    ingestion_id=ingestion_id,
                    request_digest=digest,
                    document_id=new_id("doc"),
                    metadata_json=request.model_dump(
                        mode="json", exclude={"content_base64", "media"}
                    ),
                    media_json=[
                        {
                            **m,
                            "raw_object_id": media_objects[m["object"]["key"]],
                            "media_id": new_id("media"),
                        }
                        for m in media
                    ],
                    correlation_id=request.correlation_id,
                )
            )
            return ingestion_id

    def normalization_context(self, ingestion_id: str) -> tuple[RawIngestion, str, dict[str, Any]]:
        with self.sessions() as session:
            journal = session.get(IngestionJournalRow, ingestion_id)
            row = session.get(IngestionRow, ingestion_id)
            if journal is None or row is None:
                raise LookupError("ingestion journal not found")
            return ingestion_value(session, row), journal.document_id, journal.metadata_json

    def complete(self, ingestion_id: str, document: NewsDocument) -> NewsDocument:
        with self.sessions.begin() as session:
            journal = session.scalar(
                select(IngestionJournalRow)
                .where(
                    IngestionJournalRow.ingestion_id == ingestion_id,
                )
                .with_for_update()
            )
            if journal is None:
                raise LookupError("ingestion journal not found")
            existing = session.get(DocumentRow, journal.document_id)
            if existing:
                return document_value(existing)
            ingestion = session.get(IngestionRow, ingestion_id)
            if ingestion is None:
                raise LookupError("ingestion not found")
            if (
                document.document_id != journal.document_id
                or document.ingestion_id != ingestion_id
                or document.source_id != ingestion.source_id
                or document.first_seen_at != ingestion.first_seen_at
                or document.ingested_at != ingestion.ingested_at
                or document.published_at != ingestion.published_at
            ):
                raise ValueError("normalized document disagrees with ingestion")
            session.add(DocumentRow(**document.model_dump()))
            session.flush()
            for media in journal.media_json:
                session.add(
                    MediaAssetRow(
                        media_id=media["media_id"],
                        ingestion_id=ingestion_id,
                        kind=media["kind"],
                        raw_object_id=media["raw_object_id"],
                        created_at=document.created_at,
                    )
                )
            session.flush()
            for media in journal.media_json:
                session.add(
                    DocumentMediaLinkRow(
                        document_id=document.document_id,
                        media_id=media["media_id"],
                    )
                )
            common = dict(
                occurred_at=document.created_at,
                producer="aegis.ingestion",
                correlation_id=journal.correlation_id,
            )
            stage_event(
                session,
                DocumentIngestedEvent(
                    event_id=new_id("msg"),
                    idempotency_key=f"{document.document_id}:ingested",
                    data=dict(document_id=document.document_id, ingestion_id=ingestion_id),
                    **common,
                ),
            )
            stage_event(
                session,
                DocumentNormalizedEvent(
                    event_id=new_id("msg"),
                    idempotency_key=f"{document.document_id}:normalized:1",
                    data=dict(document_id=document.document_id, revision=1),
                    **common,
                ),
            )
            session.flush()
            return document
