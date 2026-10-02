"""Run after starting the full profile; serves as the authorized test trigger."""

import asyncio
from datetime import timedelta
from uuid import uuid4

from temporalio.client import Client

from aegis.settings import get_settings
from apps.worker.workflows import FoundationWorkflow


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    result = await client.execute_workflow(
        FoundationWorkflow.run,
        "smoke",
        id=f"foundation-smoke-{uuid4()}",
        task_queue=settings.temporal_task_queue,
        execution_timeout=timedelta(seconds=30),
    )
    assert result == "AegisNews foundation: smoke"
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
