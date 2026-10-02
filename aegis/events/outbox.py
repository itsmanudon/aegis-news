"""Stage an envelope on the caller's Session; never commit or publish here."""

from sqlalchemy.orm import Session

from aegis.contracts.events import AsyncEvent
from aegis.persistence.models import OutboxRow


def stage_event(session: Session, event: AsyncEvent) -> OutboxRow:
    row = OutboxRow(
        event_id=event.event_id,
        event_type=event.event_type,
        event_version=event.event_version,
        occurred_at=event.occurred_at,
        producer=event.producer,
        correlation_id=event.correlation_id,
        idempotency_key=event.idempotency_key,
        envelope=event.model_dump(mode="json"),
    )
    session.add(row)
    return row
