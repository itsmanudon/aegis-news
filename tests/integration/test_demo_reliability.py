"""A committed AI result survives an activity failure and a worker restart."""
# ruff: noqa: F811 -- pytest fixture injection.

import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from aegis.persistence.models import AnalysisRow, DocumentRow, OutboxRow
from apps.worker.ingestion_activities import IngestionActivities
from apps.worker.intelligence_activities import IntelligenceActivities
from apps.worker.workflows import NewsIngestionWorkflow
from tests.integration.test_mvp import (  # noqa: F401
    integrated,
    repository,
    source,
    submission,
)

pytestmark = [pytest.mark.integration, pytest.mark.database]


async def test_real_retry_after_commit_and_worker_restart(integrated):
    address = os.environ.get("AEGIS_TEMPORAL_TEST_ADDRESS")
    if not address:
        pytest.skip("Requires a local Temporal server")
    service, pipeline, original, submission, _, _ = integrated
    committed = asyncio.Event()
    attempts = []
    first_counts = []

    class Interrupted(IntelligenceActivities):
        @activity.defn(name="analyze_entities")
        async def entities(self, doc_id: str, run_key: str, correlation: str) -> dict[str, str]:
            result = await self.analyze("entities", doc_id, run_key, correlation)
            attempts.append(activity.info().attempt)
            if len(attempts) == 1:
                with service.repository.sessions() as session:
                    first_counts.append(
                        session.scalar(select(func.count()).select_from(AnalysisRow))
                    )
                committed.set()
                raise RuntimeError("Controlled lost activity acknowledgement after commit")
            return result

    interrupted = Interrupted(service, original.engine, pipeline)
    ingestion = IngestionActivities(service)
    client = await Client.connect(address)
    queue, identity = "recovery-" + uuid4().hex, uuid4().hex

    def worker():
        return Worker(
            client,
            task_queue=queue,
            workflows=[NewsIngestionWorkflow],
            activities=[
                ingestion.prepare,
                ingestion.normalize,
                ingestion.commit,
                *interrupted.registered(),
            ],
        )

    async with worker():
        handle = await client.start_workflow(
            NewsIngestionWorkflow.run,
            submission.model_dump_json(),
            id=identity,
            task_queue=queue,
            execution_timeout=timedelta(seconds=90),
        )
        await asyncio.wait_for(committed.wait(), 30)
    # Temporal retains the workflow and retry while no worker is polling.
    await asyncio.sleep(1.2)
    async with worker():
        result = await asyncio.wait_for(handle.result(), 60)
    assert attempts == [1, 2]
    assert first_counts == [1]
    with service.repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(DocumentRow)) == 1
        assert session.scalar(select(func.count()).select_from(AnalysisRow)) == 6
        outbox_before = session.scalar(select(func.count()).select_from(OutboxRow))
    assert await service.prepare(submission) == result["ingestion_id"]
    await interrupted.analyze("entities", result["document_id"], identity, "retry")
    with service.repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(OutboxRow)) == outbox_before
        assert session.scalar(select(func.count()).select_from(AnalysisRow)) == 6
    assert (await pipeline.verify_document(result["document_id"], service.storage)).valid
