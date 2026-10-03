"""Transactional integration of immutable predictions and permitted materializations."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from botocore.exceptions import ClientError
from pydantic import BaseModel
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from aegis.contracts.events import AnalysisCompletedEvent, NewsEventCreatedEvent
from aegis.domain.ids import new_id
from aegis.domain.models import (
    AnalysisResult,
    Entity,
    EntityMention,
    EntityResolutionResult,
    EventExtractionResult,
    NewsDocument,
    NewsEvent,
    ProvenanceRecord,
)
from aegis.entities.materialize import materialize_mentions
from aegis.events.outbox import stage_event
from aegis.ingestion.repository import IngestionRepository, document_value, object_value
from aegis.intelligence.persistence import append_analysis, from_row
from aegis.media.storage import ObjectStorage
from aegis.persistence.models import (
    AnalysisRow,
    Base,
    DocumentMediaLinkRow,
    DocumentRow,
    EntityMentionRow,
    EntityRow,
    MediaAssetRow,
    NewsEventRow,
    ProvenanceRow,
    RawObjectRow,
)
from aegis.provenance.service import (
    ProvenanceService,
    SignedManifest,
    VerificationResult,
    canonical,
)
from aegis.security.persistence import SignedManifestRow


def stable_id(prefix: str, identity: str) -> str:
    return f"{prefix}_{uuid5(NAMESPACE_URL, identity)}"


def record[T: BaseModel](model: type[T], row: Any) -> T:
    return model.model_validate({k: getattr(row, k) for k in model.model_fields})


def event_value(session: Session, row: NewsEventRow) -> NewsEvent:
    links: dict[str, tuple[str, ...]] = {}
    for name, column in (("document", "document_id"), ("entity", "entity_id")):
        table = Base.metadata.tables["event_documents" if name == "document" else "event_entities"]
        links[f"{name}_ids"] = tuple(
            session.scalars(
                select(table.c[column])
                .where(table.c.event_id == row.event_id, table.c.revision == row.revision)
                .order_by(table.c[column])
            )
        )
    return NewsEvent.model_validate(
        {
            **{k: getattr(row, k) for k in NewsEvent.model_fields if k not in links},
            **links,
        }
    )


class AnalysisPipeline:
    def __init__(
        self, repository: IngestionRepository, provenance: ProvenanceService, key_id: str
    ) -> None:
        self.repository, self.provenance, self.key_id = repository, provenance, key_id

    def existing(self, analysis_id: str) -> AnalysisResult | None:
        with self.repository.sessions() as session:
            row = session.get(AnalysisRow, analysis_id)
            return from_row(row) if row else None

    def context(
        self, document_id: str, extraction_id: str
    ) -> tuple[tuple[EntityMention, ...], tuple[Entity, ...]]:
        with self.repository.sessions() as session:
            mentions = tuple(
                record(EntityMention, row)
                for row in session.scalars(
                    select(EntityMentionRow)
                    .where(
                        EntityMentionRow.document_id == document_id,
                        EntityMentionRow.analysis_id == extraction_id,
                    )
                    .order_by(EntityMentionRow.mention_id)
                )
            )
            # Candidates are curated canonical records, never synthesized from model spans.
            candidates = tuple(
                record(Entity, row)
                for row in session.scalars(
                    select(EntityRow).order_by(EntityRow.entity_id).limit(1000)
                )
            )
            return mentions, candidates

    def persist(self, document: NewsDocument, analysis: AnalysisResult, correlation_id: str) -> str:
        with self.repository.sessions.begin() as session:
            IngestionRepository.lock(session, analysis.analysis_id)
            if session.get(AnalysisRow, analysis.analysis_id):
                return analysis.analysis_id
            append_analysis(session, analysis)
            session.flush()
            if analysis.analysis_type == "entity_extraction":
                for extracted in materialize_mentions(document, analysis):
                    session.add(EntityMentionRow(**extracted.model_dump()))
            for index, output in enumerate(analysis.outputs):
                if isinstance(output, EntityResolutionResult):
                    mention = session.get(EntityMentionRow, output.mention_id)
                    if mention is None or mention.document_id != document.document_id:
                        raise ValueError("resolution mention does not belong to document")
                    # Keep extraction rows immutable in meaning; resolution links live in this
                    # immutable analysis. Queries join outputs to curated entities.
                    if output.entity_id and session.get(EntityRow, output.entity_id) is None:
                        raise ValueError("resolution candidate does not exist")
                if isinstance(output, EventExtractionResult) and output.confidence >= 0.5:
                    if output.evidence_text not in document.text:
                        raise ValueError("event evidence does not match document")
                    event = NewsEvent(
                        event_id=stable_id("evt", f"{analysis.analysis_id}:{index}"),
                        summary=output.evidence_text[:512],
                        document_ids=(document.document_id,),
                        occurred_at=output.occurred_at,
                        created_at=analysis.available_at,
                        available_at=analysis.available_at,
                        evidence_kind="model_output",
                        analysis_id=analysis.analysis_id,
                    )
                    session.add(
                        NewsEventRow(**event.model_dump(exclude={"document_ids", "entity_ids"}))
                    )
                    session.flush()
                    session.execute(
                        Base.metadata.tables["event_documents"]
                        .insert()
                        .values(
                            event_id=event.event_id,
                            revision=event.revision,
                            document_id=document.document_id,
                        )
                    )
                    stage_event(
                        session,
                        NewsEventCreatedEvent(
                            event_id=new_id("msg"),
                            occurred_at=analysis.available_at,
                            producer="aegis.intelligence",
                            correlation_id=correlation_id,
                            idempotency_key=f"{event.event_id}:{event.revision}",
                            data=dict(
                                event_id=event.event_id,
                                revision=event.revision,
                                available_at=event.available_at,
                            ),
                        ),
                    )
            stage_event(
                session,
                AnalysisCompletedEvent(
                    event_id=new_id("msg"),
                    occurred_at=analysis.available_at,
                    producer="aegis.intelligence",
                    correlation_id=correlation_id,
                    idempotency_key=analysis.analysis_id,
                    data=dict(
                        analysis_id=analysis.analysis_id,
                        document_id=document.document_id,
                        available_at=analysis.available_at,
                    ),
                ),
            )
        return analysis.analysis_id

    def sign(
        self, document_id: str, run_key: str, analysis_ids: list[str], raw: bytes, media: bytes
    ) -> str:
        ingestion = self.repository.get_ingestion(
            self.repository.get_document(document_id).ingestion_id
        )
        if self.provenance.crypto.hash(raw) != ingestion.object.sha256:
            raise ValueError("raw content integrity failure")
        with self.repository.sessions.begin() as session:
            IngestionRepository.lock(session, f"provenance:{run_key}")
            provenance_id = stable_id("prov", f"{run_key}:document")
            existing = session.get(ProvenanceRow, provenance_id)
            if existing:
                return provenance_id
            document = document_value(session.get(DocumentRow, document_id))  # type: ignore[arg-type]
            now = datetime.now(UTC)
            records: list[ProvenanceRecord] = []

            def add(
                subject: str,
                content: bytes,
                inputs: tuple[str, ...],
                operation: str,
                analysis_id: str | None = None,
                identity: str | None = None,
            ) -> None:
                records.append(
                    ProvenanceRecord(
                        provenance_id=stable_id("prov", identity or f"{run_key}:{subject}"),
                        subject_id=subject,
                        input_ids=inputs,
                        operation=operation,
                        recorded_at=now,
                        content_hash=self.provenance.crypto.hash(content),
                        analysis_id=analysis_id,
                    )
                )

            add(ingestion.raw_object_id, raw, (), "raw")
            add(
                document_id,
                canonical(document.model_dump(mode="json")),
                (ingestion.raw_object_id,),
                "normalization",
                identity=f"{run_key}:document",
            )
            add(f"{document_id}:media", media, (document_id,), "media_association")
            for analysis_id in analysis_ids:
                row = session.get(AnalysisRow, analysis_id)
                if row is None or row.document_id != document_id:
                    raise ValueError("analysis lineage mismatch")
                add(
                    analysis_id,
                    canonical(from_row(row).model_dump(mode="json")),
                    (document_id,),
                    "analysis",
                    analysis_id,
                )
                add(
                    f"{analysis_id}:derived",
                    self.derived_contents(session, analysis_id),
                    (analysis_id,),
                    "derived_artifact",
                    analysis_id,
                )
            manifest = self.provenance.sign(tuple(records), key_id=self.key_id)
            # Signing and immutable manifest/record writes share the caller's transaction.
            session.add(
                SignedManifestRow(
                    manifest_hash=self.provenance.crypto.hash(
                        canonical(manifest.model_dump(mode="json"))
                    ),
                    created_at=now,
                    key_id=self.key_id,
                    manifest=manifest.model_dump(mode="json"),
                )
            )
            for value in records:
                session.add(ProvenanceRow(**value.model_dump()))
        return provenance_id

    def manifests(
        self, document_id: str, provenance_id: str | None = None
    ) -> tuple[SignedManifest, ...]:
        with self.repository.sessions() as session:
            match = {"subject_id": document_id}
            if provenance_id:
                match["provenance_id"] = provenance_id
            rows = session.scalars(
                select(SignedManifestRow)
                .where(cast(SignedManifestRow.manifest["records"], JSONB).contains([match]))
                .order_by(SignedManifestRow.created_at.desc())
            )
            values = tuple(SignedManifest.model_validate(row.manifest) for row in rows)
            if not values:
                raise LookupError("signed provenance is not available")
            return values

    def manifest(self, document_id: str, provenance_id: str | None = None) -> SignedManifest:
        return self.manifests(document_id, provenance_id)[0]

    def contents(
        self, manifest: SignedManifest, raw: bytes | None, media: bytes | None = None
    ) -> dict[str, bytes]:
        contents: dict[str, bytes] = {}
        with self.repository.sessions() as session:
            for item in manifest.records:
                stored = session.get(ProvenanceRow, item.provenance_id)
                if stored is None or record(ProvenanceRecord, stored) != item:
                    continue
                value: Any = None
                if item.operation == "raw" and raw is not None:
                    contents[item.subject_id] = raw
                elif item.operation == "media_association" and media is not None:
                    contents[item.subject_id] = media
                elif item.operation == "normalization":
                    row = session.get(DocumentRow, item.subject_id)
                    value = document_value(row) if row else None
                elif item.operation == "analysis":
                    analysis = session.get(AnalysisRow, item.subject_id)
                    value = from_row(analysis) if analysis else None
                elif item.operation == "derived_artifact" and item.analysis_id:
                    contents[item.subject_id] = self.derived_contents(session, item.analysis_id)
                if value is not None:
                    contents[item.subject_id] = canonical(value.model_dump(mode="json"))
        return contents

    def media_records(self, document_id: str) -> list[dict[str, Any]]:
        with self.repository.sessions() as session:
            rows = session.execute(
                select(MediaAssetRow, RawObjectRow)
                .join(RawObjectRow, RawObjectRow.raw_object_id == MediaAssetRow.raw_object_id)
                .join(DocumentMediaLinkRow, DocumentMediaLinkRow.media_id == MediaAssetRow.media_id)
                .where(DocumentMediaLinkRow.document_id == document_id)
                .order_by(MediaAssetRow.media_id)
            )
            return [
                {
                    "document_id": document_id,
                    "media_id": media.media_id,
                    "kind": media.kind,
                    "ingestion_id": media.ingestion_id,
                    "created_at": media.created_at.isoformat(),
                    "object": object_value(raw).model_dump(mode="json"),
                }
                for media, raw in rows
            ]

    @staticmethod
    async def read_content(storage: ObjectStorage, key: str) -> bytes | None:
        try:
            return await storage.get_object(key)
        except (FileNotFoundError, KeyError):
            return None
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"NoSuchKey", "NoSuchObject", "404"}:
                return None
            raise

    async def media_snapshot(
        self, document_id: str, storage: ObjectStorage, *, signing: bool = False
    ) -> bytes:
        records = await asyncio.to_thread(self.media_records, document_id)
        for value in records:
            content = await self.read_content(storage, value["object"]["key"])
            digest = self.provenance.crypto.hash(content) if content is not None else None
            if signing and digest != value["object"]["sha256"]:
                raise ValueError("media content integrity failure")
            value["live_sha256"] = digest
        return canonical(records)

    async def verify_document(self, document_id: str, storage: ObjectStorage) -> VerificationResult:
        manifests = await asyncio.to_thread(self.manifests, document_id)
        document = await asyncio.to_thread(self.repository.get_document, document_id)
        ingestion = await asyncio.to_thread(self.repository.get_ingestion, document.ingestion_id)
        raw = await self.read_content(storage, ingestion.object.key)
        media = await self.media_snapshot(document_id, storage)
        results = []
        covered: set[str] = set()
        for manifest in manifests:
            contents = await asyncio.to_thread(self.contents, manifest, raw, media)
            results.append(await asyncio.to_thread(self.provenance.verify, manifest, contents))
            covered.update(
                item.subject_id for item in manifest.records if item.operation == "analysis"
            )

        def unsigned() -> bool:
            with self.repository.sessions() as session:
                ids = set(
                    session.scalars(
                        select(AnalysisRow.analysis_id).where(
                            AnalysisRow.document_id == document_id
                        )
                    )
                )
                return not ids <= covered

        incomplete = await asyncio.to_thread(unsigned)
        valid = all(result.valid for result in results) and not incomplete
        return VerificationResult(
            valid=valid,
            signature_valid=all(result.signature_valid for result in results),
            chain_valid=all(result.chain_valid for result in results),
            content_verified=all(result.content_verified for result in results) and not incomplete,
            reason="verified"
            if valid
            else "unsigned_intelligence"
            if incomplete
            else "verification_failed",
        )

    @staticmethod
    def derived_contents(session: Session, analysis_id: str) -> bytes:
        mentions = [
            record(EntityMention, row).model_dump(mode="json")
            for row in session.scalars(
                select(EntityMentionRow)
                .where(EntityMentionRow.analysis_id == analysis_id)
                .order_by(EntityMentionRow.mention_id)
            )
        ]
        events = [
            event_value(session, row).model_dump(mode="json")
            for row in session.scalars(
                select(NewsEventRow)
                .where(NewsEventRow.analysis_id == analysis_id)
                .order_by(NewsEventRow.event_id, NewsEventRow.revision)
            )
        ]
        return canonical({"mentions": mentions, "events": events})
