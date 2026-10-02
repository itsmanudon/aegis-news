import ast
import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from aegis.observability.logging import JsonFormatter, correlation_id_context, request_id_context
from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def test_domain_has_no_infrastructure_or_app_imports():
    for path in (ROOT / "aegis/domain").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                name = node.module or ""
                assert not name.startswith(
                    (
                        "apps",
                        "sqlalchemy",
                        "fastapi",
                        "boto3",
                        "temporalio",
                        "aegis.settings",
                        "aegis.persistence",
                    )
                )


def test_request_ids_are_bounded_and_safe():
    with TestClient(create_app()) as client:
        response = client.get(
            "/health", headers={"X-Request-ID": "x" * 129, "X-Correlation-ID": "bad value"}
        )
        assert len(response.headers["x-request-id"]) == 36
        assert len(response.headers["x-correlation-id"]) == 36


def test_json_logs_include_context_and_omit_exception_content():
    request = request_id_context.set("request-1")
    correlation = correlation_id_context.set("correlation-1")
    try:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            "file",
            1,
            "request_failed",
            (),
            (RuntimeError, RuntimeError("private-value"), None),
        )
        value = JsonFormatter().format(record)
        parsed = json.loads(value)
        assert parsed["request_id"] == "request-1"
        assert parsed["correlation_id"] == "correlation-1"
        assert "trace_id" in parsed
        assert "private-value" not in value
    finally:
        request_id_context.reset(request)
        correlation_id_context.reset(correlation)


def test_telemetry_hook_redacts_untrusted_url_attributes():
    from opentelemetry.sdk.trace import TracerProvider

    from aegis.observability.telemetry import sanitize_request_span

    provider = TracerProvider()
    try:
        with provider.get_tracer("foundation-test").start_as_current_span(
            "GET /private-path"
        ) as span:
            span.set_attribute("http.url", "http://example.test/private?token=private-value")
            sanitize_request_span(span, {"type": "http"})
            assert span.name == "HTTP request"
            assert span.attributes["http.url"] == "[redacted]"
            assert "private-value" not in str(span.attributes)
    finally:
        provider.shutdown()
