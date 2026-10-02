import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from starlette.responses import Response

from aegis.contracts.api import (
    ApiErrorEnvelope,
    ErrorCode,
    HealthStatus,
    ReadinessStatus,
    ResponseMeta,
    SingleResponse,
    SystemInfo,
)
from aegis.observability.logging import (
    configure_logging,
    correlation_id_context,
    request_id_context,
)
from aegis.observability.telemetry import instrument
from aegis.settings import Settings, get_settings
from apps.api.dependencies import ReadinessProbe
from apps.api.errors import error_response, install_handlers
from apps.api.routes import assets, documents, entities, events, search

logger = logging.getLogger("aegis.api")
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def safe_id(value: str | None) -> str:
    return value if value and ID_PATTERN.fullmatch(value) else str(uuid4())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    registry = CollectorRegistry()
    requests = Counter(
        "aegis_http_requests_total",
        "HTTP requests",
        ["method", "route", "status"],
        registry=registry,
    )
    duration = Histogram(
        "aegis_http_request_duration_seconds",
        "HTTP duration",
        ["method", "route"],
        registry=registry,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_file)
        app.state.probe = ReadinessProbe(settings)
        try:
            yield
        finally:
            await app.state.probe.close()

    app = FastAPI(
        title="AegisNews",
        version="0.1.0",
        description=(
            "Foundation-only modular monolith. Domain routes are reserved, not implemented."
        ),
        lifespan=lifespan,
        responses={422: {"model": ApiErrorEnvelope}, 500: {"model": ApiErrorEnvelope}},
        openapi_tags=[
            {"name": n, "description": "Reserved for the next product phase"}
            for n in ("documents", "entities", "events", "search", "assets")
        ],
    )
    install_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["X-Request-ID", "X-Correlation-ID"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    @app.middleware("http")
    async def context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = safe_id(request.headers.get("x-request-id"))
        correlation_id = safe_id(request.headers.get("x-correlation-id") or request_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request_token = request_id_context.set(request_id)
        correlation_token = correlation_id_context.set(correlation_id)
        start = perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.error("request_failed", extra={"error_type": type(exc).__name__})
                response = error_response(
                    request, ErrorCode.INTERNAL_ERROR, "Internal server error", 500
                )
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            route = getattr(request.scope.get("route"), "path", "unmatched")
            elapsed = perf_counter() - start
            requests.labels(request.method, route, str(response.status_code)).inc()
            duration.labels(request.method, route).observe(elapsed)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "route": route,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed * 1000, 3),
                },
            )
            return response
        finally:
            request_id_context.reset(request_token)
            correlation_id_context.reset(correlation_token)

    @app.get("/health", response_model=SingleResponse[HealthStatus], tags=["system"])
    async def health(request: Request) -> SingleResponse[HealthStatus]:
        return SingleResponse(
            data=HealthStatus(), meta=ResponseMeta(request_id=request.state.request_id)
        )

    @app.get(
        "/ready",
        response_model=SingleResponse[ReadinessStatus],
        responses={503: {"model": ApiErrorEnvelope}},
        tags=["system"],
    )
    async def ready(request: Request) -> SingleResponse[ReadinessStatus] | Response:
        checks = await request.app.state.probe.check()
        if not all(c.ready for c in checks):
            logger.warning("dependencies_not_ready")
            return error_response(
                request, ErrorCode.SOURCE_UNAVAILABLE, "Required dependencies are not ready", 503
            )
        return SingleResponse(
            data=ReadinessStatus(status="ready", dependencies=checks),
            meta=ResponseMeta(request_id=request.state.request_id),
        )

    @app.get("/api/v1/system/info", response_model=SingleResponse[SystemInfo], tags=["system"])
    async def system_info(request: Request) -> SingleResponse[SystemInfo]:
        return SingleResponse(
            data=SystemInfo(version="0.1.0"), meta=ResponseMeta(request_id=request.state.request_id)
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            generate_latest(registry), media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    for module in (documents, entities, events, search, assets):
        app.include_router(module.router, prefix="/api/v1")
    instrument(app, settings)
    return app


app = create_app()
