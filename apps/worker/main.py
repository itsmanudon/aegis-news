import asyncio

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

from aegis.ingestion.runtime import make_service
from aegis.intelligence.engine import build_engine
from aegis.intelligence.pipeline import AnalysisPipeline
from aegis.observability.logging import configure_logging
from aegis.observability.telemetry import configure_tracing
from aegis.provenance.service import ProvenanceService
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.keys import FileKeyProvider
from aegis.settings import get_settings
from apps.worker.activities import foundation_echo
from apps.worker.ingestion_activities import IngestionActivities
from apps.worker.intelligence_activities import IntelligenceActivities
from apps.worker.workflows import FoundationWorkflow, NewsIngestionWorkflow


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_file)
    tracing = configure_tracing(settings, "aegisnews-worker")
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        interceptors=[TracingInterceptor()] if settings.otel_enabled else [],
    )
    service = make_service(settings)
    ingestion = IngestionActivities(service)
    intelligence = IntelligenceActivities(
        service,
        build_engine(settings.ai_profile),
        AnalysisPipeline(
            service.repository,
            ProvenanceService(
                StandardCryptoProvider(FileKeyProvider(settings.security_key_directory))
            ),
            settings.provenance_key_id,
        ),
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[FoundationWorkflow, NewsIngestionWorkflow],
        activities=[
            foundation_echo,
            ingestion.prepare,
            ingestion.normalize,
            ingestion.commit,
            *intelligence.registered(),
        ],
    )
    try:
        await worker.run()
    finally:
        service.repository.close()
        if tracing:
            await asyncio.to_thread(tracing.shutdown)


if __name__ == "__main__":
    asyncio.run(main())
