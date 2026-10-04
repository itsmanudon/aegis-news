from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from aegis.contracts.events import DocumentNormalizedEvent
from aegis.domain.ids import new_id
from aegis.domain.models import AnalysisResult
from aegis.events.outbox import stage_event
from aegis.persistence.database import make_engine
from aegis.persistence.models import (
    AnalysisRow,
    DocumentMediaLinkRow,
    DocumentRow,
    IngestionRow,
    MediaAssetRow,
    OutboxRow,
    RawObjectRow,
    SourceRow,
)
from aegis.settings import get_settings
from apps.api.dependencies import ReadinessProbe

pytestmark = pytest.mark.integration


@pytest.fixture
def engine():
    engine = make_engine(get_settings())
    yield engine
    engine.dispose()


def seed_document(session, document, now):
    raw_id = new_id("raw")
    session.add(
        SourceRow(source_id=document.source_id, name="Synthetic", kind="upload", created_at=now)
    )
    session.add(
        RawObjectRow(
            raw_object_id=raw_id,
            bucket="test",
            key=str(uuid4()),
            sha256="0" * 64,
            size_bytes=0,
            content_type="text/plain",
            created_at=now,
        )
    )
    session.flush()
    session.add(
        IngestionRow(
            ingestion_id=document.ingestion_id,
            source_id=document.source_id,
            raw_object_id=raw_id,
            first_seen_at=now,
            ingested_at=now,
            idempotency_key=str(uuid4()),
        )
    )
    session.flush()
    session.add(DocumentRow(**document.model_dump()))
    session.flush()


async def test_live_dependencies_and_storage_roundtrip():
    probe = ReadinessProbe(get_settings())
    key = f"foundation-tests/{uuid4()}"
    try:
        assert all(d.ready for d in await probe.check())
        storage = probe.storage
        assert not await storage.exists(key)
        await storage.put_object(key, b"synthetic fixture", "text/plain")
        assert await storage.get_object(key) == b"synthetic fixture"
        assert await storage.exists(key)
        assert (await storage.metadata(key)).size_bytes == len(b"synthetic fixture")
    finally:
        await probe.storage.delete_object(key)
        await probe.close()


@pytest.mark.database
def test_extensions_and_schema(engine):
    with engine.connect() as connection:
        names = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
        assert {"vector", "pg_trgm"} <= names
        assert "outbox_events" in inspect(connection).get_table_names()
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "live_providers_0001"
        )


@pytest.mark.database
def test_domain_write_and_outbox_are_atomic(engine, document, now):
    event = DocumentNormalizedEvent(
        event_id=new_id("msg"),
        occurred_at=now,
        producer="integration",
        correlation_id="test",
        idempotency_key=str(uuid4()),
        data=dict(document_id=document.document_id, revision=1),
    )
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            with Session(connection, join_transaction_mode="create_savepoint") as session:
                with session.begin():
                    seed_document(session, document, now)
                    stage_event(session, event)
                assert session.get(DocumentRow, document.document_id) is not None
                assert (
                    session.get(OutboxRow, event.event_id).envelope["data"]["document_id"]
                    == document.document_id
                )
                duplicate = event.model_copy(update={"event_id": new_id("msg")})
                with pytest.raises(IntegrityError), session.begin_nested():
                    stage_event(session, duplicate)
                    session.flush()
                rollback_document = document.model_copy(
                    update={
                        "document_id": new_id("doc"),
                        "ingestion_id": new_id("ing"),
                        "source_id": new_id("src"),
                    }
                )
                rollback_event = event.model_copy(
                    update={"event_id": new_id("msg"), "idempotency_key": str(uuid4())}
                )
                with pytest.raises(RuntimeError), session.begin_nested():
                    seed_document(session, rollback_document, now)
                    stage_event(session, rollback_event)
                    session.flush()
                    raise RuntimeError("synthetic transaction failure")
                assert session.get(DocumentRow, rollback_document.document_id) is None
                assert session.get(OutboxRow, rollback_event.event_id) is None
        finally:
            outer.rollback()


@pytest.mark.database
@pytest.mark.parametrize(
    "output",
    [
        dict(result_type="topic", label="notice", confidence=0.9),
        dict(
            result_type="entity_extraction",
            surface="Example",
            start_offset=0,
            end_offset=7,
            confidence=0.9,
        ),
        dict(result_type="embedding", values=[0.1, -0.2]),
        dict(
            result_type="event_extraction",
            proposed_event_type="notice",
            confidence=0.8,
            evidence_text="published a notice",
        ),
        dict(
            result_type="event_classification",
            event_id=new_id("evt"),
            event_revision=2,
            label="notice",
            confidence=0.8,
        ),
    ],
)
def test_analysis_append_only_and_time_constraints(engine, document, analysis, now, output):
    if output["result_type"] == "event_extraction":
        output = {**output, "document_id": document.document_id}
    analysis = AnalysisResult.model_validate(
        {
            **analysis.model_dump(),
            "analysis_type": output["result_type"],
            "outputs": [output],
        }
    )
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            with Session(connection, join_transaction_mode="create_savepoint") as session:
                seed_document(session, document, now)
                data = analysis.model_dump(mode="python")
                data["outputs"] = [o.model_dump(mode="json") for o in analysis.outputs]
                session.add(AnalysisRow(**data))
                session.flush()
                for statement in (
                    "UPDATE analyses SET model_version = '2' WHERE analysis_id = :id",
                    "DELETE FROM analyses WHERE analysis_id = :id",
                    "TRUNCATE analyses CASCADE",
                ):
                    with pytest.raises(DBAPIError), session.begin_nested():
                        session.execute(text(statement), {"id": analysis.analysis_id})
                assert session.get(AnalysisRow, analysis.analysis_id).model_version == "1"
                stored = session.get(AnalysisRow, analysis.analysis_id)
                assert stored.outputs == [o.model_dump(mode="json") for o in analysis.outputs]
                next_run = {
                    **data,
                    "analysis_id": new_id("ana"),
                    "model_version": "2",
                    "created_at": now + timedelta(seconds=1),
                    "available_at": now + timedelta(seconds=2),
                }
                session.add(AnalysisRow(**next_run))
                session.flush()
                assert session.get(AnalysisRow, analysis.analysis_id).model_version == "1"
                assert session.get(AnalysisRow, next_run["analysis_id"]).available_at > now
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        AnalysisRow(
                            **{
                                **data,
                                "analysis_id": new_id("ana"),
                                "available_at": now - timedelta(seconds=1),
                            }
                        )
                    )
                    session.flush()
        finally:
            outer.rollback()


@pytest.mark.database
def test_explicit_document_media_links_and_foreign_keys(engine, document, now):
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            with Session(connection, join_transaction_mode="create_savepoint") as session:
                seed_document(session, document, now)
                # A second document from the same raw ingestion is permitted.
                second = document.model_copy(update={"document_id": new_id("doc")})
                session.add(DocumentRow(**second.model_dump()))
                # Media can originate from a different ingestion; association is explicit.
                other = document.model_copy(
                    update={
                        "document_id": new_id("doc"),
                        "ingestion_id": new_id("ing"),
                        "source_id": new_id("src"),
                    }
                )
                seed_document(session, other, now)
                raw_id = session.get(IngestionRow, other.ingestion_id).raw_object_id
                media_ids = [new_id("media"), new_id("media")]
                for media_id in media_ids:
                    session.add(
                        MediaAssetRow(
                            media_id=media_id,
                            ingestion_id=other.ingestion_id,
                            kind="image",
                            raw_object_id=raw_id,
                            created_at=now,
                        )
                    )
                session.flush()
                assert (
                    session.query(DocumentMediaLinkRow)
                    .filter_by(document_id=document.document_id)
                    .count()
                    == 0
                )
                pairs = [
                    (document.document_id, media_ids[0]),
                    (document.document_id, media_ids[1]),
                    (second.document_id, media_ids[0]),
                ]
                for document_id, media_id in pairs:
                    session.add(DocumentMediaLinkRow(document_id=document_id, media_id=media_id))
                session.flush()
                assert (
                    session.query(DocumentMediaLinkRow)
                    .filter_by(document_id=document.document_id)
                    .count()
                    == 2
                )
                assert (
                    session.query(DocumentMediaLinkRow).filter_by(media_id=media_ids[0]).count()
                    == 2
                )
                for document_id, media_id in (
                    (new_id("doc"), media_ids[0]),
                    (document.document_id, new_id("media")),
                    pairs[0],  # Duplicate links are rejected as well.
                ):
                    with pytest.raises(IntegrityError), session.begin_nested():
                        session.add(
                            DocumentMediaLinkRow(document_id=document_id, media_id=media_id)
                        )
                        session.flush()
        finally:
            outer.rollback()


async def test_temporal_worker_executes_workflow():
    from temporalio.client import Client

    from apps.worker.workflows import FoundationWorkflow

    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    result = await client.execute_workflow(
        FoundationWorkflow.run,
        "integration",
        id=f"foundation-integration-{uuid4()}",
        task_queue=settings.temporal_task_queue,
        execution_timeout=timedelta(seconds=30),
    )
    assert result == "AegisNews foundation: integration"
