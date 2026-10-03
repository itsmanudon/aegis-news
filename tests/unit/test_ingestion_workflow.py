from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
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

    async with await WorkflowEnvironment.start_local() as env:
        queue = "test-ingestion-" + uuid4().hex
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[NewsIngestionWorkflow],
            activities=[prepare, normalize, commit],
        ):
            result = await env.client.execute_workflow(
                NewsIngestionWorkflow.run,
                "valid",
                id=uuid4().hex,
                task_queue=queue,
                execution_timeout=timedelta(seconds=60),
            )
            assert result["document_id"] == "document"
            assert attempts == [("valid", 1), ("valid", 2)]
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


async def test_workflow_dispatches_three_activities(monkeypatch):
    from apps.worker import workflows

    calls = []

    async def execute(name, value=None, **options):
        calls.append((name, value, options))
        return {
            "prepare_ingestion": "ing",
            "normalize_ingestion": "json",
            "commit_ingestion": {"ingestion_id": "ing", "document_id": "doc"},
        }[name]

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "now", lambda: datetime.now(UTC))
    result = await NewsIngestionWorkflow().run("request-json")
    assert result["document_id"] == "doc"
    assert [call[0] for call in calls] == [
        "prepare_ingestion",
        "normalize_ingestion",
        "commit_ingestion",
    ]
    assert all(c[2]["retry_policy"].maximum_attempts == 5 for c in calls)
