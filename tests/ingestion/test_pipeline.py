"""Real PostgreSQL transactions; storage fake deliberately retains bytes across DB failure."""

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from aegis.domain.ids import new_id
from aegis.domain.models import Source
from aegis.ingestion.inputs import IngestionRequest, MediaInput
from aegis.ingestion.repository import IngestionJournalRow, IngestionRepository
from aegis.ingestion.service import IngestionService
from aegis.media.storage import ObjectMetadata
from aegis.persistence.models import (
    Base,
    DocumentMediaLinkRow,
    DocumentRow,
    IngestionRow,
    MediaAssetRow,
    OutboxRow,
    RawObjectRow,
)


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.writes = 0

    async def put_object(self, key, content, content_type):
        self.objects[key] = (content, content_type)
        self.writes += 1

    async def exists(self, key):
        return key in self.objects

    async def get_object(self, key):
        return self.objects[key][0]

    async def metadata(self, key):
        content, mime = self.objects[key]
        return ObjectMetadata(size_bytes=len(content), content_type=mime)

    async def delete_object(self, key):
        self.objects.pop(key, None)


@pytest.fixture
def repository():
    url = os.environ.get("AEGIS_INGESTION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set AEGIS_INGESTION_TEST_DATABASE_URL to a disposable PostgreSQL database")
    root = create_engine(url)
    schema = "ingestion_test_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    repo = IngestionRepository(sessionmaker(engine, expire_on_commit=False))
    yield repo
    engine.dispose()
    with root.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    root.dispose()


@pytest.fixture
def source(repository):
    source = Source(
        source_id=new_id("src"), name="Offline", kind="upload", created_at=datetime.now(UTC)
    )
    return repository.create_source(source)


@pytest.fixture
def submission(source):
    return IngestionRequest(
        source_id=source.source_id,
        idempotency_key="fixture-1",
        content_type="application/json",
        content_base64=base64.b64encode(
            b'{"title":"Historic notice","text":"Example body.",'
            b'"published_at":"1999-02-03T04:05:06Z","language":"en"}'
        ).decode(),
        first_seen_at=datetime(2020, 1, 1, tzinfo=UTC),
        media=(
            MediaInput(
                kind="attachment",
                content_type="text/plain",
                content_base64=base64.b64encode(b"supporting evidence").decode(),
            ),
        ),
    )


def count(repository, model):
    with repository.sessions() as session:
        return session.scalar(select(func.count()).select_from(model))


async def run_pipeline(service, submission):
    ingestion_id = await service.prepare(submission)
    document = await service.normalize(ingestion_id)
    return service.complete(ingestion_id, document)


async def test_duplicate_creates_one_document_and_two_events(repository, submission):
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    first = await run_pipeline(service, submission)
    second = await run_pipeline(service, submission.model_copy(update={"correlation_id": "retry"}))
    assert first == second
    assert count(repository, IngestionRow) == count(repository, DocumentRow) == 1
    assert count(repository, OutboxRow) == 2
    assert storage.writes == 2
    assert any(
        v[0] == base64.b64decode(submission.content_base64) for v in storage.objects.values()
    )
    assert first.published_at == datetime(1999, 2, 3, 4, 5, 6, tzinfo=UTC)
    assert first.first_seen_at == submission.first_seen_at
    assert first.first_seen_at <= first.ingested_at <= first.created_at
    assert first.revision == 1 and first.language == "en"
    assert repository.get_document(first.document_id) == first
    assert repository.get_ingestion(first.ingestion_id).object.sha256
    assert count(repository, MediaAssetRow) == count(repository, DocumentMediaLinkRow) == 1
    with repository.sessions() as session:
        link = session.scalar(select(DocumentMediaLinkRow))
        asset = session.get(MediaAssetRow, link.media_id)
        assert link.document_id == first.document_id
        assert asset.ingestion_id == first.ingestion_id
        assert {e.event_type for e in session.scalars(select(OutboxRow))} == {
            "document.ingested.v1",
            "document.normalized.v1",
        }


async def test_conflicting_retry_is_rejected(repository, submission):
    service = IngestionService(repository, MemoryStorage(), "test")
    await run_pipeline(service, submission)
    with pytest.raises(ValueError, match="idempotency"):
        await service.prepare(submission.model_copy(update={"title": "Changed"}))
    assert count(repository, IngestionRow) == 1


async def test_object_write_then_db_failure_recovers(repository, submission, monkeypatch):
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    persist = repository.persist_ingestion
    monkeypatch.setattr(
        repository,
        "persist_ingestion",
        lambda *args: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    with pytest.raises(RuntimeError, match="db down"):
        await service.prepare(submission)
    assert len(storage.objects) == 2
    assert count(repository, IngestionRow) == count(repository, RawObjectRow) == 0
    monkeypatch.setattr(repository, "persist_ingestion", persist)
    await run_pipeline(service, submission)
    assert storage.writes == 2
    assert count(repository, RawObjectRow) == 2


async def test_outbox_failure_rolls_back_document_links_and_media(
    repository, submission, monkeypatch
):
    import aegis.ingestion.repository as module

    service = IngestionService(repository, MemoryStorage(), "test")
    ingestion_id = await service.prepare(submission)
    document = await service.normalize(ingestion_id)
    original = module.stage_event

    def fail_after_stage(session, event):
        original(session, event)
        session.flush()
        raise RuntimeError("outbox failure")

    monkeypatch.setattr(module, "stage_event", fail_after_stage)
    with pytest.raises(RuntimeError):
        service.complete(ingestion_id, document)
    for model in (DocumentRow, MediaAssetRow, DocumentMediaLinkRow, OutboxRow):
        assert count(repository, model) == 0
    assert count(repository, IngestionJournalRow) == 1
    monkeypatch.setattr(module, "stage_event", original)
    assert service.complete(ingestion_id, document).document_id == document.document_id
    assert count(repository, OutboxRow) == 2


async def test_concurrent_completion_is_retry_safe(repository, submission):
    service = IngestionService(repository, MemoryStorage(), "test")
    ingestion_id = await service.prepare(submission)
    document = await service.normalize(ingestion_id)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.complete(ingestion_id, document), range(4)))
    assert all(r == results[0] for r in results)
    assert count(repository, DocumentRow) == 1
    assert count(repository, OutboxRow) == 2


async def test_same_bytes_with_different_keys_share_objects_not_documents(repository, submission):
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    first = await run_pipeline(service, submission)
    second = await run_pipeline(
        service, submission.model_copy(update={"idempotency_key": "different"})
    )
    assert first.document_id != second.document_id
    assert count(repository, RawObjectRow) == 2
    assert count(repository, IngestionRow) == count(repository, DocumentRow) == 2
    assert count(repository, OutboxRow) == 4


def test_source_api_persistence_and_retrieval(repository):
    from fastapi.testclient import TestClient

    from aegis.settings import Settings
    from apps.api.main import create_app

    app = create_app(Settings())
    app.state.ingestion_service = IngestionService(repository, MemoryStorage(), "test")
    with TestClient(app) as http:
        response = http.post(
            "/api/v1/sources",
            json={
                "name": "Historical archive",
                "kind": "upload",
                "url": "https://example.org/archive",
            },
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Historical archive" and data["kind"] == "upload"
        retrieved = http.get("/api/v1/sources/" + data["source_id"]).json()["data"]
        assert Source.model_validate(retrieved) == Source.model_validate(data)
        assert http.get("/api/v1/sources/" + new_id("src")).status_code == 404


async def test_real_temporal_submission_identity_and_status(repository, submission):
    from datetime import timedelta

    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from aegis.ingestion.submissions import TemporalSubmissions
    from aegis.settings import Settings
    from apps.worker.ingestion_activities import IngestionActivities
    from apps.worker.workflows import NewsIngestionWorkflow

    if os.environ.get("AEGIS_INGESTION_TEST_TEMPORAL") != "1":
        pytest.skip("Set AEGIS_INGESTION_TEST_TEMPORAL=1 to run an SDK local Temporal server")
    activities = IngestionActivities(IngestionService(repository, MemoryStorage(), "test"))
    async with await WorkflowEnvironment.start_local() as env:
        queue = "test-ingestion-" + uuid4().hex
        client = TemporalSubmissions(Settings(temporal_task_queue=queue))
        client.client = env.client
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[NewsIngestionWorkflow],
            activities=[activities.prepare, activities.normalize, activities.commit],
        ):
            first = await client.submit(submission)
            second = await client.submit(submission)
            assert first == second
            await env.client.get_workflow_handle(first["workflow_id"]).result(
                rpc_timeout=timedelta(seconds=60),
            )
            third = await client.submit(submission)
            assert third == first
            status = await client.status(first["workflow_id"])
            assert status["status"] == "COMPLETED"
            assert repository.get_document(status["result"]["document_id"])
            with pytest.raises(LookupError):
                await client.status("missing-" + uuid4().hex)
    assert count(repository, OutboxRow) == 2


async def test_concurrent_prepare_returns_one_ingestion(repository, submission):
    import asyncio

    service = IngestionService(repository, MemoryStorage(), "test")
    results = await asyncio.gather(*(service.prepare(submission) for _ in range(4)))
    assert len(set(results)) == 1
    assert count(repository, IngestionRow) == 1
    assert count(repository, IngestionJournalRow) == 1


def test_journal_migration_upgrade_downgrade_upgrade(repository):
    import importlib

    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    migration = importlib.import_module("migrations.versions.ingestion_0001")
    assert migration.down_revision == "0002_contract_hardening"
    with repository.sessions.begin() as session:
        connection = session.connection()
        IngestionJournalRow.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "ingestion_journal" in inspect(connection).get_table_names()
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            migration.downgrade()
            assert "ingestion_journal" not in inspect(connection).get_table_names()
            migration.upgrade()
            assert "ingestion_journal" in inspect(connection).get_table_names()


async def test_unknown_source_and_invalid_media_write_nothing(repository, submission):
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    with pytest.raises(LookupError):
        await service.prepare(submission.model_copy(update={"source_id": new_id("src")}))
    bad = MediaInput(kind="image", content_type="image/png", content_base64="YWJj")
    with pytest.raises(ValueError):
        await service.prepare(submission.model_copy(update={"media": (bad,)}))
    assert storage.objects == {}


async def test_image_storage_and_explicit_association(repository, submission):
    image = MediaInput(
        kind="image",
        content_type="image/png",
        content_base64=(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a"
            "l1sAAAAASUVORK5CYII="
        ),
    )
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    document = await run_pipeline(service, submission.model_copy(update={"media": (image,)}))
    with repository.sessions() as session:
        link = session.scalar(select(DocumentMediaLinkRow))
        asset = session.get(MediaAssetRow, link.media_id)
        raw = session.get(RawObjectRow, asset.raw_object_id)
        assert asset.kind == "image" and link.document_id == document.document_id
        assert raw.content_type == "image/png"
        assert await storage.get_object(raw.key) == base64.b64decode(image.content_base64)


async def test_corrupt_stored_bytes_stop_normalization(repository, submission):
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    ingestion_id = await service.prepare(submission)
    ref = repository.get_ingestion(ingestion_id).object
    storage.objects[ref.key] = (b"tampered", ref.content_type)
    with pytest.raises(ValueError, match="hash"):
        await service.normalize(ingestion_id)
    assert count(repository, DocumentRow) == 0


async def test_default_observation_precedes_object_write(repository, submission):
    class TimedStorage(MemoryStorage):
        async def put_object(self, key, content, content_type):
            self.first_write_at = datetime.now(UTC)
            await super().put_object(key, content, content_type)

    storage = TimedStorage()
    service = IngestionService(repository, storage, "test")
    document = await run_pipeline(service, submission.model_copy(update={"first_seen_at": None}))
    assert document.first_seen_at <= storage.first_write_at


async def test_temporal_pipeline_with_real_activities_and_api(repository, submission):
    from datetime import timedelta

    from fastapi.testclient import TestClient
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from aegis.settings import Settings
    from apps.api.main import create_app
    from apps.worker.ingestion_activities import IngestionActivities
    from apps.worker.workflows import NewsIngestionWorkflow

    if os.environ.get("AEGIS_INGESTION_TEST_TEMPORAL") != "1":
        pytest.skip("Set AEGIS_INGESTION_TEST_TEMPORAL=1 to run an SDK local Temporal server")
    storage = MemoryStorage()
    service = IngestionService(repository, storage, "test")
    activities = IngestionActivities(service)
    async with await WorkflowEnvironment.start_local() as env:
        queue = "test-ingestion-" + uuid4().hex
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[NewsIngestionWorkflow],
            activities=[activities.prepare, activities.normalize, activities.commit],
        ):
            result = await env.client.execute_workflow(
                NewsIngestionWorkflow.run,
                submission.model_dump_json(),
                id=uuid4().hex,
                task_queue=queue,
                execution_timeout=timedelta(seconds=60),
            )
    document = repository.get_document(result["document_id"])
    assert result["ingestion_id"] == document.ingestion_id
    assert count(repository, DocumentMediaLinkRow) == 1
    assert count(repository, OutboxRow) == 2
    app = create_app(Settings())
    app.state.ingestion_service = service
    with TestClient(app) as http:
        response = http.get("/api/v1/documents/" + result["document_id"])
        assert response.status_code == 200
        assert response.json()["data"] == document.model_dump(mode="json")
        raw = http.get("/api/v1/ingestions/" + result["ingestion_id"])
        assert raw.status_code == 200
        assert raw.json()["data"]["object"]["key"] in storage.objects
        assert http.get("/api/v1/documents/" + new_id("doc")).status_code == 404


async def test_live_minio_temporal_acceptance(repository, submission):
    from datetime import timedelta

    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from aegis.media.s3 import S3ObjectStorage
    from apps.worker.ingestion_activities import IngestionActivities
    from apps.worker.workflows import NewsIngestionWorkflow

    endpoint = os.environ.get("AEGIS_INGESTION_TEST_MINIO")
    if not endpoint:
        pytest.skip("Set AEGIS_INGESTION_TEST_MINIO to a disposable MinIO endpoint")
    bucket = "ingestion-test-" + uuid4().hex
    storage = S3ObjectStorage(
        endpoint_url=endpoint,
        access_key="aegis_dev",
        secret_key="aegis_dev_only",
        bucket=bucket,
        region="us-east-1",
    )
    storage.client.create_bucket(Bucket=bucket)
    service = IngestionService(repository, storage, bucket)
    activities = IngestionActivities(service)
    try:
        async with await WorkflowEnvironment.start_local() as env:
            queue = "test-ingestion-" + uuid4().hex
            async with Worker(
                env.client,
                task_queue=queue,
                workflows=[NewsIngestionWorkflow],
                activities=[activities.prepare, activities.normalize, activities.commit],
            ):
                result = await env.client.execute_workflow(
                    NewsIngestionWorkflow.run,
                    submission.model_dump_json(),
                    id=uuid4().hex,
                    task_queue=queue,
                    execution_timeout=timedelta(seconds=60),
                )
        ingestion = repository.get_ingestion(result["ingestion_id"])
        assert await storage.get_object(ingestion.object.key) == base64.b64decode(
            submission.content_base64
        )
        assert repository.get_document(result["document_id"]).title == "Historic notice"
        assert count(repository, DocumentMediaLinkRow) == 1
        assert count(repository, OutboxRow) == 2
        from fastapi.testclient import TestClient

        from aegis.settings import Settings
        from apps.api.main import create_app

        app = create_app(Settings())
        app.state.ingestion_service = service
        with TestClient(app) as http:
            response = http.get("/api/v1/documents/" + result["document_id"])
            assert response.status_code == 200
            assert response.json()["data"]["document_id"] == result["document_id"]
    finally:
        for item in storage.client.list_objects_v2(Bucket=bucket).get("Contents", []):
            await storage.delete_object(item["Key"])
        storage.client.delete_bucket(Bucket=bucket)
