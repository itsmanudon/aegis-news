import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.workflows import NewsIngestionWorkflow


@pytest.mark.integration
async def test_real_temporal_retries_and_terminal_validation():
    attempts = []
    committed = []

    @activity.defn(name="prepare_ingestion")
    async def prepare(value: str, observed_at: str) -> str:
        assert datetime.fromisoformat(observed_at).tzinfo is not None
        attempts.append((value, activity.info().attempt))
        if value == "invalid":
            raise ApplicationError("invalid input", type="InvalidIngestion", non_retryable=True)
        if activity.info().attempt == 1:
            raise RuntimeError("transient storage failure")
        return "ingestion"

    @activity.defn(name="normalize_ingestion")
    async def normalize(value: str) -> str:
        assert value == "ingestion"
        return "document-json"

    @activity.defn(name="commit_ingestion")
    async def commit(value: str) -> dict[str, str]:
        assert value == "document-json"
        committed.append(value)
        return {"ingestion_id": "ingestion", "document_id": "document"}

    extra = []
    for name in (
        "analyze_entities",
        "analyze_topics",
        "analyze_sentiment",
        "generate_embedding",
        "resolve_entities",
        "extract_events",
    ):

        async def analyze(document_id: str, run_key: str, correlation_id: str) -> dict[str, str]:
            return {"status": "unavailable", "reason": "NoPredictions"}

        extra.append(activity.defn(name=name)(analyze))

    @activity.defn(name="record_provenance")
    async def provenance(document_id: str, run_key: str, ids: list[str]) -> str:
        return "provenance"

    extra.append(provenance)
    address = os.environ.get("AEGIS_TEMPORAL_TEST_ADDRESS")
    environment = (
        WorkflowEnvironment.from_client(await Client.connect(address))
        if address
        else await WorkflowEnvironment.start_local()
    )
    async with environment as env:
        queue = "test-ingestion-" + uuid4().hex
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[NewsIngestionWorkflow],
            activities=[prepare, normalize, commit, *extra],
        ):
            result = await env.client.execute_workflow(
                NewsIngestionWorkflow.run,
                "{}",
                id=uuid4().hex,
                task_queue=queue,
                execution_timeout=timedelta(seconds=60),
            )
            assert result["document_id"] == "document"
            assert attempts == [("{}", 1), ("{}", 2)]
            assert committed == ["document-json"]
            with pytest.raises(WorkflowFailureError):
                await env.client.execute_workflow(
                    NewsIngestionWorkflow.run,
                    "invalid",
                    id=uuid4().hex,
                    task_queue=queue,
                    execution_timeout=timedelta(seconds=60),
                )
            assert attempts[-1] == ("invalid", 1)


async def test_workflow_dispatches_integrated_activities(monkeypatch):
    from apps.worker import workflows

    calls = []

    async def execute(name, value=None, **options):
        calls.append((name, value, options))
        return {
            "prepare_ingestion": "ing",
            "normalize_ingestion": "json",
            "commit_ingestion": {"ingestion_id": "ing", "document_id": "doc"},
        }.get(
            name,
            "provenance"
            if name == "record_provenance"
            else {"status": "completed", "analysis_id": "analysis"},
        )

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "now", lambda: datetime.now(UTC))
    monkeypatch.setattr(workflows.workflow, "info", lambda: SimpleNamespace(workflow_id="test-run"))
    result = await NewsIngestionWorkflow().run("{}")
    assert result["document_id"] == "doc"
    assert [call[0] for call in calls] == [
        "prepare_ingestion",
        "normalize_ingestion",
        "commit_ingestion",
        "analyze_entities",
        "analyze_topics",
        "analyze_sentiment",
        "generate_embedding",
        "resolve_entities",
        "extract_events",
        "record_provenance",
    ]
    assert all(c[2]["retry_policy"].maximum_attempts == 5 for c in calls)
