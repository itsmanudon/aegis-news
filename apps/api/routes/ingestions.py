import asyncio
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from temporalio.service import RPCError

from aegis.contracts.api import ErrorCode, ResponseMeta, SingleResponse
from aegis.domain.ids import new_id
from aegis.domain.models import NewsDocument, NonEmpty, RawIngestion, Source
from aegis.ingestion.inputs import IngestionRequest, decode_content, decode_media
from aegis.ingestion.repository import IngestionRepository
from aegis.ingestion.runtime import make_service
from aegis.ingestion.submissions import TemporalSubmissions
from aegis.normalization.article import parse_article
from apps.api.errors import ApiException

router = APIRouter(tags=["ingestion"])


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: NonEmpty
    kind: Literal["feed", "api", "upload", "web"]
    url: HttpUrl | None = None


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: tuple[IngestionRequest, ...] = Field(min_length=1, max_length=20)


def repository(request: Request) -> IngestionRepository:
    if not hasattr(request.app.state, "ingestion_service"):
        request.app.state.ingestion_service = make_service(request.app.state.settings)
    service_repository: IngestionRepository = request.app.state.ingestion_service.repository
    return service_repository


def submissions(request: Request) -> TemporalSubmissions:
    if not hasattr(request.app.state, "ingestion_submissions"):
        settings = request.app.state.settings
        if not settings.temporal_enabled:
            raise ApiException(ErrorCode.SOURCE_UNAVAILABLE, "Temporal ingestion is disabled", 503)
        request.app.state.ingestion_submissions = TemporalSubmissions(settings)
    client: TemporalSubmissions = request.app.state.ingestion_submissions
    return client


def validate(request: IngestionRequest) -> None:
    try:
        parse_article(decode_content(request), request.content_type)
        for media in request.media:
            decode_media(media)
    except ValueError as exc:
        raise ApiException(ErrorCode.INVALID_ARGUMENT, "Invalid ingestion content", 422) from exc


def response(request: Request, data: Any) -> SingleResponse[Any]:
    return SingleResponse(data=data, meta=ResponseMeta(request_id=request.state.request_id))


@router.post("/sources", response_model=SingleResponse[Source], status_code=201)
def create_source(body: SourceCreate, request: Request) -> SingleResponse[Any]:
    source = Source(
        source_id=new_id("src"),
        name=body.name,
        kind=body.kind,
        url=body.url,
        created_at=datetime.now(UTC),
    )
    return response(request, repository(request).create_source(source))


@router.get("/sources/{source_id}", response_model=SingleResponse[Source])
def get_source(source_id: str, request: Request) -> SingleResponse[Any]:
    try:
        return response(request, repository(request).get_source(source_id))
    except LookupError as exc:
        raise ApiException(ErrorCode.NOT_FOUND, "Source not found", 404) from exc


@router.post("/ingestions", response_model=SingleResponse[dict[str, str]], status_code=202)
async def submit(body: IngestionRequest, request: Request) -> SingleResponse[Any]:
    validate(body)
    try:
        return response(request, await submissions(request).submit(body))
    except (RPCError, TimeoutError, OSError) as exc:
        raise ApiException(ErrorCode.SOURCE_UNAVAILABLE, "Temporal unavailable", 503) from exc


@router.post("/ingestions/batch", response_model=SingleResponse[dict[str, Any]], status_code=202)
async def submit_batch(body: BatchRequest, request: Request) -> SingleResponse[Any]:
    for item in body.items:
        validate(item)
    client = submissions(request)
    try:
        results = [await client.submit(item) for item in body.items]
    except (RPCError, TimeoutError, OSError) as exc:
        raise ApiException(
            ErrorCode.SOURCE_UNAVAILABLE, "Batch submission interrupted; retry the same batch", 503
        ) from exc
    return response(request, {"submissions": results})


@router.get("/ingestion-runs/{workflow_id}", response_model=SingleResponse[dict[str, Any]])
async def get_run(workflow_id: str, request: Request) -> SingleResponse[Any]:
    try:
        return response(request, await submissions(request).status(workflow_id))
    except LookupError as exc:
        raise ApiException(ErrorCode.NOT_FOUND, "Ingestion run not found", 404) from exc
    except (RPCError, TimeoutError, OSError) as exc:
        raise ApiException(ErrorCode.SOURCE_UNAVAILABLE, "Temporal unavailable", 503) from exc


@router.get("/ingestions/{ingestion_id}", response_model=SingleResponse[RawIngestion])
async def get_ingestion(ingestion_id: str, request: Request) -> SingleResponse[Any]:
    try:
        value = await asyncio.to_thread(repository(request).get_ingestion, ingestion_id)
        return response(request, value)
    except LookupError as exc:
        raise ApiException(ErrorCode.NOT_FOUND, "Ingestion not found", 404) from exc


@router.get("/documents/{document_id}", response_model=SingleResponse[NewsDocument])
async def get_document(document_id: str, request: Request) -> SingleResponse[Any]:
    try:
        value = await asyncio.to_thread(repository(request).get_document, document_id)
        return response(request, value)
    except LookupError as exc:
        raise ApiException(ErrorCode.NOT_FOUND, "Document not found", 404) from exc
