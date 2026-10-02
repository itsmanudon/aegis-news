import json
import logging
import logging.handlers
from contextvars import ContextVar
from datetime import UTC, datetime

from opentelemetry import trace

request_id_context: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span().get_span_context()
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
            "correlation_id": correlation_id_context.get(),
            "trace_id": f"{span.trace_id:032x}" if span.is_valid else None,
            "span_id": f"{span.span_id:016x}" if span.is_valid else None,
        }
        for name in ("method", "route", "status_code", "duration_ms", "error_type"):
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        # Deliberately omit exception text/tracebacks, URLs and request payloads.
        return json.dumps(payload)


def configure_logging(log_file: str = "") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10_000_000, backupCount=2
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
    root.setLevel(logging.INFO)
