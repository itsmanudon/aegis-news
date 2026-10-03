"""Allowlisted security events: no arbitrary payloads, credentials or token claims."""

import hashlib
import logging
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

ACTIONS = frozenset(
    {
        "authentication_success",
        "authentication_failure",
        "permission_denied",
        "sensitive_document_read",
        "source_modification",
        "integrity_verification",
        "signature_verification",
        "security_change",
        "admin_change",
        "rate_limit_denied",
    }
)


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    occurred_at: datetime
    action: str
    actor_hash: str | None = None
    subject_hash: str | None = None
    request_id: str = ""
    outcome: str = "attempt"


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...
    def recent(self, limit: int) -> tuple[AuditEvent, ...]: ...


class MemoryAuditSink:
    """Bounded, process-local development sink. Production uses SQLAuditSink."""

    def __init__(self) -> None:
        self._events: deque[AuditEvent] = deque(maxlen=10000)
        self._lock = Lock()

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def recent(self, limit: int) -> tuple[AuditEvent, ...]:
        return self.events[-max(1, min(limit, 100)) :][::-1]


class AuditLog:
    def __init__(self, sink: AuditSink) -> None:
        self.sink = sink

    def emit(
        self,
        action: str,
        *,
        actor: str | None = None,
        subject: str | None = None,
        request_id: str = "",
        outcome: str = "attempt",
        **discarded: Any,
    ) -> None:
        if action not in ACTIONS or outcome not in {"attempt", "success", "failure"}:
            raise ValueError("Unknown audit action or outcome")

        # Hash untrusted identities/subjects; discard every non-allowlisted field.
        def digest(value: str | None) -> str | None:
            return hashlib.sha256(value.encode()).hexdigest() if value else None

        import re

        event = AuditEvent(
            event_id=str(uuid4()),
            occurred_at=datetime.now(UTC),
            action=action,
            actor_hash=digest(actor),
            subject_hash=digest(subject),
            request_id=request_id if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", request_id) else "",
            outcome=outcome,
        )
        self.sink.append(event)  # Failure propagates: sensitive operations fail closed.
        logging.getLogger("aegis.audit").info(
            "security_audit", extra={"audit_event": event.model_dump(mode="json")}
        )
