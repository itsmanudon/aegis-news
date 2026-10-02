import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from aegis.observability.logging import configure_logging
from aegis.settings import get_settings
from apps.worker.activities import foundation_echo
from apps.worker.workflows import FoundationWorkflow


async def main() -> None:
    configure_logging()
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[FoundationWorkflow],
        activities=[foundation_echo],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
