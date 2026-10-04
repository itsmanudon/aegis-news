"""Scope-protected manual runs, acquisition evidence and expiring video references."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request

from aegis.contracts.api import CollectionResponse, CursorPagination, ResponseMeta, SingleResponse
from aegis.persistence.database import make_engine, session_factory
from aegis.providers.adapters import YouTubeProvider
from aegis.providers.models import (
    NAMES,
    ArticleEvidence,
    FetchOptions,
    ProviderArticleView,
    ProviderName,
    ProviderRun,
    ProviderStatus,
    YouTubeReference,
)
from aegis.providers.persistence import ProviderStore
from aegis.providers.service import IngestionGateway, ProviderRunner
from aegis.providers.transport import ProviderError, ProviderHttp, make_http_client
from aegis.security.auth import product_access
from apps.api.routes.ingestions import audit_action, submissions

router = APIRouter(tags=["providers"])
Write = [product_access("sources:write"), product_access("ingestions:write")]
Read = [product_access("documents:read")]
Limit = Annotated[int, Query(ge=1, le=100)]


def runner(request: Request) -> ProviderRunner:
    return runner_from_app(request.app)


def runner_from_app(app: FastAPI) -> ProviderRunner:
    if not hasattr(app.state, "provider_runner"):
        engine = make_engine(app.state.settings)
        app.state.provider_engine = engine
        app.state.provider_runner = ProviderRunner(
            app.state.settings,
            ProviderStore(session_factory(engine)),
            app.state.provider_metrics,
        )
    result: ProviderRunner = app.state.provider_runner
    return result


def meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


async def initialize(app: FastAPI, service: ProviderRunner) -> None:
    async with app.state.provider_initialization_lock:
        if not app.state.provider_initialized:
            await asyncio.to_thread(service.store.interrupt_runs)
            app.state.provider_initialized = True


@router.get(
    "/providers", response_model=SingleResponse[tuple[ProviderStatus, ...]], dependencies=Write
)
def providers(request: Request) -> SingleResponse[tuple[ProviderStatus, ...]]:
    return SingleResponse(data=runner(request).statuses(), meta=meta(request))


async def begin(
    names: list[ProviderName], body: FetchOptions, request: Request
) -> SingleResponse[ProviderRun]:
    service = runner(request)
    # One bounded run per local API. No unbounded background queue/continuous polling.
    if request.app.state.provider_active:
        raise HTTPException(409, detail="A provider run is already active")
    request.app.state.provider_active = True
    report = ProviderRun(run_id=str(uuid4()), created_at=datetime.now(UTC), status="running")
    try:
        await initialize(request.app, service)
        await asyncio.to_thread(audit_action, request, "provider_fetch", report.run_id)
        await asyncio.to_thread(service.store.run, report)
    except Exception:
        request.app.state.provider_active = False
        raise
    authorization = request.headers.get("Authorization", "")

    async def work() -> None:
        try:
            async with make_http_client() as client:
                gateway = IngestionGateway(
                    client, service.settings.provider_ingestion_api_url, authorization
                )
                await service.execute(names, body, gateway, report=report)
        except Exception:
            interrupted = report.model_copy(update={"status": "interrupted"})
            await asyncio.to_thread(service.store.run, interrupted)
        finally:
            request.app.state.provider_active = False

    task = asyncio.create_task(work())
    request.app.state.provider_tasks.add(task)
    task.add_done_callback(request.app.state.provider_tasks.discard)
    return SingleResponse(data=report, meta=meta(request))


@router.post(
    "/providers/fetch-all",
    response_model=SingleResponse[ProviderRun],
    status_code=202,
    dependencies=Write,
)
async def fetch_all(body: FetchOptions, request: Request) -> SingleResponse[ProviderRun]:
    return await begin(list(NAMES), body, request)


@router.post(
    "/providers/{provider}/fetch",
    response_model=SingleResponse[ProviderRun],
    status_code=202,
    dependencies=Write,
)
async def fetch(
    provider: ProviderName, body: FetchOptions, request: Request
) -> SingleResponse[ProviderRun]:
    return await begin([provider], body, request)


@router.get(
    "/provider-runs/{run_id}", response_model=SingleResponse[ProviderRun], dependencies=Write
)
async def get_run(run_id: str, request: Request) -> SingleResponse[ProviderRun]:
    service = runner(request)
    report = await asyncio.to_thread(service.store.get_run, run_id)
    if report is None:
        raise HTTPException(404)
    # Canonical completion is recorded only after the actual Temporal result.
    statuses: dict[str, str] = {}
    for workflow_id in {w for outcome in report.outcomes for w in outcome.workflow_ids}:
        try:
            state = await submissions(request).status(workflow_id)
            statuses[workflow_id] = state["status"]
            if state.get("status") == "COMPLETED":
                await asyncio.to_thread(
                    service.store.completed, workflow_id, state["result"]["document_id"]
                )
        except Exception:
            statuses[workflow_id] = "UNAVAILABLE"
    return SingleResponse(
        data=report.model_copy(update={"workflow_statuses": statuses}), meta=meta(request)
    )


@router.get(
    "/provider-articles", response_model=CollectionResponse[ProviderArticleView], dependencies=Read
)
def article_list(
    request: Request, limit: Limit = 20, cursor: Annotated[str | None, Query(max_length=128)] = None
) -> CollectionResponse[ProviderArticleView]:
    try:
        values = runner(request).store.article_page(limit + 1, cursor)
    except ValueError:
        raise HTTPException(422, detail="Invalid acquisition cursor") from None
    more = len(values) > limit
    return CollectionResponse(
        data=tuple(values[:limit]),
        pagination=CursorPagination(
            has_more=more,
            next_cursor=(
                values[limit - 1].acquired_at.isoformat() + "|" + values[limit - 1].article_id
            )
            if more
            else None,
        ),
        meta=meta(request),
    )


@router.get(
    "/documents/{document_id}/acquisition",
    response_model=SingleResponse[tuple[ArticleEvidence, ...]],
    dependencies=Read,
)
def acquisition(document_id: str, request: Request) -> SingleResponse[tuple[ArticleEvidence, ...]]:
    return SingleResponse(data=runner(request).store.evidence(document_id), meta=meta(request))


@router.get(
    "/youtube-references", response_model=CollectionResponse[YouTubeReference], dependencies=Read
)
def video_list(
    request: Request, limit: Limit = 20, cursor: Annotated[str | None, Query(max_length=11)] = None
) -> CollectionResponse[YouTubeReference]:
    values = runner(request).store.video_page(limit + 1, cursor)
    more = len(values) > limit
    return CollectionResponse(
        data=tuple(values[:limit]),
        pagination=CursorPagination(
            has_more=more, next_cursor=values[limit - 1].video_id if more else None
        ),
        meta=meta(request),
    )


@router.post(
    "/youtube-references/refresh", response_model=SingleResponse[dict[str, int]], dependencies=Write
)
async def refresh(request: Request) -> SingleResponse[dict[str, int]]:
    service = runner(request)
    values = await asyncio.to_thread(service.store.video_page, 50, None)
    try:
        async with make_http_client() as client:
            references = await YouTubeProvider(
                ProviderHttp(client), service.key("youtube")
            ).refresh([v.video_id for v in values])
    except ProviderError as exc:
        raise HTTPException(503, detail="YouTube refresh unavailable: " + exc.code) from None
    await asyncio.to_thread(
        service.store.refresh_videos, [v.video_id for v in values], list(references)
    )
    await asyncio.to_thread(audit_action, request, "provider_fetch", "youtube-refresh")
    return SingleResponse(
        data={"refreshed": len(references), "deleted": len(values) - len(references)},
        meta=meta(request),
    )


@router.delete(
    "/youtube-references/{video_id}",
    response_model=SingleResponse[dict[str, str]],
    dependencies=Write,
)
def delete_video(video_id: str, request: Request) -> SingleResponse[dict[str, str]]:
    runner(request).store.refresh_videos([video_id], [])
    audit_action(request, "source_modification", "youtube-delete:" + video_id)
    return SingleResponse(data={"status": "deleted"}, meta=meta(request))
