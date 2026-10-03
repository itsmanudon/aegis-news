from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span
from starlette.types import Scope

from aegis.settings import Settings


def sanitize_request_span(span: Span, scope: Scope) -> None:
    """Route templates may be retained; raw URLs/queries are not evidence."""
    if span.is_recording():
        for attribute in ("http.url", "http.target", "url.full", "url.query"):
            span.set_attribute(attribute, "[redacted]")
        span.update_name("HTTP request")


def configure_tracing(settings: Settings, service_name: str) -> TracerProvider | None:
    if not settings.otel_enabled:
        return None
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
    )
    trace.set_tracer_provider(provider)
    return provider


def instrument(app: FastAPI, settings: Settings) -> None:
    provider = configure_tracing(settings, "aegisnews-api")
    if provider is None:
        return
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="health,metrics",
        server_request_hook=sanitize_request_span,
        exclude_spans=["receive", "send"],
    )
