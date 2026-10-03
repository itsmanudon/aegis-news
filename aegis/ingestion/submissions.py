"""Temporal submissions: identity survives retries and never substitutes tracing IDs."""

import asyncio
import hashlib
from contextlib import suppress
from datetime import timedelta
from typing import Any

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from aegis.ingestion.inputs import IngestionRequest, fingerprint
from aegis.settings import Settings
from apps.worker.workflows import NewsIngestionWorkflow


def workflow_identity(request: IngestionRequest) -> str:
    identity = f"{request.source_id}:{request.idempotency_key}:{fingerprint(request)}"
    return "ingestion-" + hashlib.sha256(identity.encode()).hexdigest()


class TemporalSubmissions:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Client | None = None
        self.lock = asyncio.Lock()

    async def connect(self) -> Client:
        async with self.lock:
            if self.client is None:
                try:
                    self.client = await asyncio.wait_for(
                        Client.connect(
                            self.settings.temporal_address,
                            namespace=self.settings.temporal_namespace,
                            interceptors=[TracingInterceptor()]
                            if self.settings.otel_enabled
                            else [],
                        ),
                        timeout=5,
                    )
                except RuntimeError as exc:
                    raise ConnectionError("Temporal unavailable") from exc
            assert self.client is not None
            return self.client

    async def submit(self, request: IngestionRequest) -> dict[str, str]:
        client = await self.connect()
        workflow_id = workflow_identity(request)
        with suppress(WorkflowAlreadyStartedError):
            await client.start_workflow(
                NewsIngestionWorkflow.run,
                request.model_dump_json(),
                id=workflow_id,
                task_queue=self.settings.temporal_task_queue,
                execution_timeout=timedelta(minutes=15),
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                rpc_timeout=timedelta(seconds=5),
            )
        return {"workflow_id": workflow_id}

    async def status(self, workflow_id: str) -> dict[str, Any]:
        client = await self.connect()
        handle = client.get_workflow_handle(workflow_id)
        try:
            description = await handle.describe(rpc_timeout=timedelta(seconds=5))
        except RPCError as exc:
            if exc.status == RPCStatusCode.NOT_FOUND:
                raise LookupError("workflow not found") from exc
            raise
        result = None
        if description.status == WorkflowExecutionStatus.COMPLETED:
            result = await handle.result(rpc_timeout=timedelta(seconds=5))
        return {
            "workflow_id": workflow_id,
            "status": description.status.name if description.status else "UNKNOWN",
            "result": result,
        }
