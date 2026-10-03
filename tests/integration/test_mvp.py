"""Exercise the real integration seams using PostgreSQL and real crypto, offline AI."""
# ruff: noqa: F811 -- imported pytest fixtures are dependency-injected by name.

import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from aegis.domain.ids import new_id
from aegis.domain.models import Entity
from aegis.ingestion.service import IngestionService
from aegis.intelligence.engine import build_engine
from aegis.intelligence.pipeline import AnalysisPipeline
from aegis.persistence.models import (
    AnalysisRow,
    DocumentRow,
    EntityMentionRow,
    EntityRow,
    NewsEventRow,
    OutboxRow,
)
from aegis.provenance.service import ProvenanceService
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider, generate_development_keys
from aegis.settings import Settings
from apps.api.main import create_app
from apps.worker.intelligence_activities import IntelligenceActivities
from tests.ingestion.test_pipeline import (  # noqa: F401
    MemoryStorage,
    repository,
    source,
    submission,
)

pytestmark = [pytest.mark.integration, pytest.mark.database]


@pytest.fixture
def integrated(repository, source, submission, tmp_path):
    generate_development_keys(tmp_path, "local")
    crypto = StandardCryptoProvider(FileKeyProvider(tmp_path))
    service = IngestionService(repository, MemoryStorage(), "test")
    pipeline = AnalysisPipeline(repository, ProvenanceService(crypto), "local")
    worker = IntelligenceActivities(service, build_engine("offline"), pipeline)
    text = (
        "Atlas Labs announced a merger and strong profit growth. Atlas Labs launched new software."
    )
    submission = submission.model_copy(
        update={
            "content_type": "text/plain",
            "content_base64": base64.b64encode(text.encode()).decode(),
            "language": "en",
            "title": "Synthetic business technology news",
        }
    )
    entity = Entity(
        entity_id=new_id("ent"),
        canonical_name="Atlas Labs",
        kind="organization",
        created_at=datetime.now(UTC),
    )
    with repository.sessions.begin() as session:
        session.add(EntityRow(**entity.model_dump()))
    return service, pipeline, worker, submission, tmp_path, entity


async def processed(integrated):
    service, pipeline, worker, submission, _, _ = integrated
    ingestion_id = await service.prepare(submission)
    doc = service.complete(ingestion_id, await service.normalize(ingestion_id))
    run_key = uuid4().hex
    ids = []
    for task in ("entities", "topics", "sentiment", "embedding", "resolution", "events"):
        result = await worker.analyze(task, doc.document_id, run_key, "seam-test")
        assert result["status"] == "completed"
        ids.append(result["analysis_id"])
    await worker.provenance(doc.document_id, run_key, ids)
    return doc, run_key, ids


async def test_analysis_materialization_retry_rerun_provenance_tamper(integrated):
    service, pipeline, worker, submission, _, entity = integrated
    doc, run_key, ids = await processed(integrated)
    with service.repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRow)) == 6
        mentions = list(session.scalars(select(EntityMentionRow)))
        assert mentions and all(
            m.evidence_kind == "model_output" and m.analysis_id == ids[0] for m in mentions
        )
        assert all(m.entity_id is None for m in mentions)
        resolution = session.get(AnalysisRow, ids[4])
        assert all(o["entity_id"] == entity.entity_id for o in resolution.outputs)
        assert session.scalar(select(func.count()).select_from(NewsEventRow)) >= 1
        count = session.scalar(select(func.count()).select_from(OutboxRow))
    assert await service.prepare(submission) == doc.ingestion_id
    assert (await worker.analyze("entities", doc.document_id, run_key, "retry"))[
        "analysis_id"
    ] == ids[0]
    await worker.provenance(doc.document_id, run_key, ids)
    with service.repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(OutboxRow)) == count
    manifest = pipeline.manifest(doc.document_id)
    raw = await service.storage.get_object(
        service.repository.get_ingestion(doc.ingestion_id).object.key
    )
    media = await pipeline.media_snapshot(doc.document_id, service.storage)
    assert pipeline.provenance.verify(manifest, pipeline.contents(manifest, raw, media)).valid
    assert not pipeline.provenance.verify(
        manifest, pipeline.contents(manifest, raw + b"tamper", media)
    ).valid
    with service.repository.sessions.begin() as session:
        session.get(DocumentRow, doc.document_id).text += " tampered"
    assert not pipeline.provenance.verify(manifest, pipeline.contents(manifest, raw, media)).valid
    rerun = await worker.analyze("topics", doc.document_id, uuid4().hex, "rerun")
    assert rerun["analysis_id"] not in ids


async def test_product_auth_queries_cutoff_and_live_verification(integrated):
    service, _, _, _, keys_path, entity = integrated
    doc, _, _ = await processed(integrated)
    settings = Settings(
        _env_file=None,
        environment="test",
        security_enabled=True,
        dev_identity_enabled=True,
        oidc_issuer="https://local.test",
        oidc_audience="aegisnews",
        oidc_algorithms=["EdDSA"],
        oidc_public_keys={"local": (keys_path / "local.ed25519.pub").read_text()},
        security_key_directory=keys_path,
        security_rate_limit=1000,
    )
    app = create_app(settings)
    app.state.ingestion_service = service
    keys = FileKeyProvider(keys_path)

    def headers(role):
        return {
            "Authorization": "Bearer "
            + issue_development_token(settings, keys, key_id="local", subject="demo", role=role)
        }

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/documents").status_code == 401
        analyst = headers("analyst")
        for path in ("/sources", "/ingestions", "/ingestions/batch"):
            assert client.post("/api/v1" + path, headers=analyst, json={}).status_code == 403
        response = client.get(f"/api/v1/documents/{doc.document_id}/intelligence", headers=analyst)
        assert response.status_code == 200, response.text
        value = response.json()["data"]
        assert len(value["analyses"]) == 6 and value["media"] and value["entities"]
        assert client.get("/api/v1/search", params={"q": "Atlas"}, headers=analyst).json()["data"]
        assert client.get(f"/api/v1/entities/{entity.entity_id}/documents", headers=analyst).json()[
            "data"
        ]
        cutoff = (doc.created_at - timedelta(seconds=1)).isoformat()
        assert (
            client.get("/api/v1/documents", params={"as_of": cutoff}, headers=analyst).json()[
                "data"
            ]
            == []
        )
        result = client.post(f"/api/v1/documents/{doc.document_id}/verify", headers=analyst)
        assert result.status_code == 200, result.text
        assert result.json()["data"]["valid"]
        assert client.get("/api/v1/security/audit", headers=analyst).status_code == 403
        assert client.get("/api/v1/security/audit", headers=headers("admin")).status_code == 200
        # An event revision can become available after its producing analysis.
        # A historical intelligence response must enforce both cutoffs.
        from aegis.persistence.models import Base

        cutoff = datetime.now(UTC)
        with service.repository.sessions.begin() as session:
            original = session.scalar(select(NewsEventRow))
            future = NewsEventRow(
                event_id=original.event_id,
                revision=2,
                summary="Future revision",
                created_at=cutoff + timedelta(days=1),
                available_at=cutoff + timedelta(days=1),
                evidence_kind="model_output",
                analysis_id=original.analysis_id,
            )
            session.add(future)
            session.flush()
            session.execute(
                Base.metadata.tables["event_documents"]
                .insert()
                .values(event_id=original.event_id, revision=2, document_id=doc.document_id)
            )
        historical = client.get(
            f"/api/v1/documents/{doc.document_id}/intelligence",
            params={"as_of": cutoff.isoformat()},
            headers=analyst,
        ).json()["data"]
        assert all(value["revision"] == 1 for value in historical["events"])


async def test_missing_models_degrade_without_losing_document(integrated):
    from aegis.intelligence.errors import ModelUnavailable

    service, _, worker, submission, _, _ = integrated
    ingestion_id = await service.prepare(submission)
    doc = service.complete(ingestion_id, await service.normalize(ingestion_id))

    class Missing:
        async def extract(self, document):
            raise ModelUnavailable("not installed")

    from dataclasses import replace

    worker.engine = replace(worker.engine, entities=Missing())
    assert await worker.analyze("entities", doc.document_id, "missing", "test") == {
        "status": "unavailable",
        "reason": "ModelUnavailable",
    }
    assert service.repository.get_document(doc.document_id) == doc


async def test_complete_temporal_workflow(integrated):
    import os

    from temporalio.client import Client
    from temporalio.worker import Worker

    from apps.worker.ingestion_activities import IngestionActivities
    from apps.worker.workflows import NewsIngestionWorkflow

    address = os.environ.get("AEGIS_TEMPORAL_TEST_ADDRESS")
    if not address:
        pytest.skip("Set AEGIS_TEMPORAL_TEST_ADDRESS for real workflow seam")
    service, pipeline, intelligence, submission, _, _ = integrated
    ingestion = IngestionActivities(service)
    client = await Client.connect(address)
    queue = "integration-" + uuid4().hex
    async with Worker(
        client,
        task_queue=queue,
        workflows=[NewsIngestionWorkflow],
        activities=[
            ingestion.prepare,
            ingestion.normalize,
            ingestion.commit,
            *intelligence.registered(),
        ],
    ):
        result = await client.execute_workflow(
            NewsIngestionWorkflow.run,
            submission.model_dump_json(),
            id=uuid4().hex,
            task_queue=queue,
            execution_timeout=timedelta(seconds=90),
        )
    assert result["analyze_topics"] == "completed"
    assert result["extract_events"] == "completed"
    assert pipeline.manifest(result["document_id"]).signature


async def test_provenance_reruns_media_and_old_derived_tampering(integrated):
    service, pipeline, worker, _, _, _ = integrated
    doc, first_run, first_ids = await processed(integrated)
    second_run = uuid4().hex
    second = await worker.analyze("topics", doc.document_id, second_run, "rerun")
    await worker.provenance(doc.document_id, second_run, [second["analysis_id"]])
    # A retry must retrieve its own manifest, even after a later run has signed.
    await worker.provenance(doc.document_id, first_run, first_ids)
    assert (await pipeline.verify_document(doc.document_id, service.storage)).valid
    with service.repository.sessions.begin() as session:
        mention = session.scalar(select(EntityMentionRow))
        mention_id, surface = mention.mention_id, mention.surface
        mention.surface = "Tampered"
    assert not (await pipeline.verify_document(doc.document_id, service.storage)).valid
    with service.repository.sessions.begin() as session:
        session.get(EntityMentionRow, mention_id).surface = surface
    assert (await pipeline.verify_document(doc.document_id, service.storage)).valid
    media_key = next(key for key in service.storage.objects if "/media/" in key)
    original = service.storage.objects[media_key]
    service.storage.objects[media_key] = (b"tampered attachment", original[1])
    assert not (await pipeline.verify_document(doc.document_id, service.storage)).valid
    service.storage.objects[media_key] = original
    from aegis.persistence.models import DocumentMediaLinkRow

    with service.repository.sessions.begin() as session:
        session.delete(session.scalar(select(DocumentMediaLinkRow)))
    assert not (await pipeline.verify_document(doc.document_id, service.storage)).valid
