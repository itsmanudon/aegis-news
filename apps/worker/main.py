import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from aegis.ingestion.runtime import make_service
from aegis.observability.logging import configure_logging
from aegis.settings import get_settings
from apps.worker.activities import foundation_echo
from apps.worker.ingestion_activities import IngestionActivities
from apps.worker.workflows import FoundationWorkflow, NewsIngestionWorkflow


async def main() -> None:
    configure_logging()
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    service = make_service(settings)
    ingestion = IngestionActivities(service)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[FoundationWorkflow, NewsIngestionWorkflow],
        activities=[foundation_echo, ingestion.prepare, ingestion.normalize, ingestion.commit],
    )
    try:
        await worker.run()
    finally:
        service.repository.close()


if __name__ == "__main__":
    asyncio.run(main())
