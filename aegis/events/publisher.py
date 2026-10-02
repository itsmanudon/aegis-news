from typing import Protocol

from aegis.contracts.events import AsyncEvent


class EventPublisher(Protocol):
    async def publish(self, event: AsyncEvent) -> None:
        """Publish at least once; consumers deduplicate on event_id/idempotency_key."""
        ...


class LocalEventPublisher:
    """Explicit no-op for foundation development; never represents durable delivery."""

    async def publish(self, event: AsyncEvent) -> None:
        return None
