import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from redis.asyncio import Redis
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
from aegis.ingestion.http import IngestionBodyLimit
from aegis.observability.logging import (
    configure_logging,
    correlation_id_context,
    request_id_context,
)
from aegis.observability.telemetry import instrument
from aegis.persistence.database import make_engine
from aegis.provenance.service import ProvenanceService
from aegis.security.abuse import MemoryRateLimiter, RedisRateLimiter
from aegis.security.audit import AuditLog, MemoryAuditSink
from aegis.security.auth import TokenValidator, require_scopes
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.keys import FileKeyProvider
from aegis.security.middleware import SecurityBodyLimit
from aegis.security.persistence import SQLAuditSink, SQLManifestStore
from aegis.settings import Settings, get_settings
from apps.api.dependencies import ReadinessProbe
from apps.api.errors import error_response, install_handlers
from apps.api.routes import (
    assets,
    documents,
    entities,
    events,
    ingestions,
    product,
    search,
    security,
)

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
            if hasattr(app.state, "ingestion_service"):
                app.state.ingestion_service.repository.close()
            if app.state.security_redis is not None:
                await app.state.security_redis.aclose()
            if app.state.audit_engine is not None:
                app.state.audit_engine.dispose()

    app = FastAPI(
        title="AegisNews",
        version="0.1.0",
        description=(
            "Modular monolith with durable offline ingestion and canonical document retrieval."
        ),
        lifespan=lifespan,
        responses={422: {"model": ApiErrorEnvelope}, 500: {"model": ApiErrorEnvelope}},
        openapi_tags=[
            {"name": n, "description": "Canonical product records"}
            for n in ("documents", "entities", "events", "search", "assets")
        ],
    )
    install_handlers(app)
    app.state.settings = settings
    app.add_middleware(IngestionBodyLimit)
    if settings.security_enabled:
        app.add_middleware(SecurityBodyLimit, max_bytes=settings.security_max_body_bytes)
    public_keys = dict(settings.oidc_public_keys)
    if settings.dev_identity_enabled:
        key_path = settings.security_key_directory / f"{settings.provenance_key_id}.ed25519.pub"
        if key_path.exists():
            public_keys[settings.provenance_key_id] = key_path.read_text()
    app.state.token_validator = TokenValidator(settings, public_keys=public_keys)
    app.state.audit_engine = (
        make_engine(settings)
        if settings.environment == "production" or settings.security_persist_audit
        else None
    )
    app.state.audit = AuditLog(
        SQLAuditSink(app.state.audit_engine) if app.state.audit_engine else MemoryAuditSink()
    )
    app.state.provenance = ProvenanceService(
        StandardCryptoProvider(FileKeyProvider(settings.security_key_directory)),
        SQLManifestStore(app.state.audit_engine) if app.state.audit_engine else None,
    )
    app.state.security_redis = (
        Redis.from_url(
            settings.redis_url.get_secret_value(), socket_connect_timeout=2, socket_timeout=2
        )
        if settings.security_rate_backend == "redis"
        else None
    )
    app.state.rate_limiter = (
        RedisRateLimiter(app.state.security_redis, settings.security_rate_limit)
        if app.state.security_redis
        else MemoryRateLimiter(settings.security_rate_limit)
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
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
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            if settings.security_enabled and request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"
            if settings.environment == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000"
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

    for module, scope in (
        (documents, "documents:read"),
        (entities, "documents:read"),
        (events, "events:read"),
        (search, "documents:read"),
        (assets, "documents:read"),
    ):
        app.include_router(
            module.router,
            prefix="/api/v1",
            dependencies=[require_scopes(scope)] if settings.security_enabled else [],
        )
    if settings.security_enabled:
        app.include_router(security.router, prefix="/api/v1")
    app.include_router(ingestions.router, prefix="/api/v1")
    app.include_router(product.router, prefix="/api/v1")
    instrument(app, settings)
    return app


app = create_app()
