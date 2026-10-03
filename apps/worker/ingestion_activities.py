import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

from temporalio import activity
from temporalio.exceptions import ApplicationError

from aegis.domain.models import NewsDocument
from aegis.ingestion.inputs import IngestionRequest
from aegis.ingestion.service import IngestionService


async def terminal_errors[T](operation: Callable[[], Awaitable[T]]) -> T:
    try:
        return await operation()
    except LookupError as exc:
        raise ApplicationError(
            "source or ingestion not found", type="InvalidIngestion", non_retryable=True
        ) from exc
    except ValueError as exc:
        raise ApplicationError(
            "invalid or conflicting ingestion", type="InvalidIngestion", non_retryable=True
        ) from exc


class IngestionActivities:
    def __init__(self, service: IngestionService) -> None:
        self.service = service

    @activity.defn(name="prepare_ingestion")
    async def prepare(self, request_json: str, observed_at: str) -> str:
        async def operation() -> str:
            request = IngestionRequest.model_validate_json(request_json)
            return await self.service.prepare(request, datetime.fromisoformat(observed_at))

        return await terminal_errors(operation)

    @activity.defn(name="normalize_ingestion")
    async def normalize(self, ingestion_id: str) -> str:
        async def operation() -> str:
            document = await self.service.normalize(ingestion_id)
            return document.model_dump_json()

        return await terminal_errors(operation)

    @activity.defn(name="commit_ingestion")
    async def commit(self, document_json: str) -> dict[str, str]:
        async def operation() -> dict[str, str]:
            document = NewsDocument.model_validate_json(document_json)
            result = await asyncio.to_thread(
                self.service.complete,
                document.ingestion_id,
                document,
            )
            return {"ingestion_id": result.ingestion_id, "document_id": result.document_id}

        return await terminal_errors(operation)
