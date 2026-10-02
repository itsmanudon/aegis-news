import asyncio

from redis.asyncio import Redis
from sqlalchemy import text
from temporalio.client import Client

from aegis.contracts.api import DependencyStatus
from aegis.media.s3 import S3ObjectStorage
from aegis.persistence.database import make_engine
from aegis.settings import Settings


class ReadinessProbe:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = make_engine(settings)
        self.redis: Redis = Redis.from_url(
            settings.redis_url.get_secret_value(), socket_connect_timeout=2, socket_timeout=2
        )
        self.storage = S3ObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key.get_secret_value(),
            secret_key=settings.s3_secret_key.get_secret_value(),
            bucket=settings.s3_bucket,
            region=settings.s3_region,
        )

    def _postgres(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            # A reachable database with no migration is not ready.
            connection.execute(text("SELECT event_id FROM outbox_events LIMIT 0"))

    async def check(self) -> tuple[DependencyStatus, ...]:
        async def check_one(name: str) -> DependencyStatus:
            try:
                async with asyncio.timeout(5):
                    if name == "postgres":
                        await asyncio.to_thread(self._postgres)
                    elif name == "redis":
                        await self.redis.ping()
                    elif name == "object_storage":
                        await self.storage.ready()
                    else:
                        client = await Client.connect(
                            self.settings.temporal_address,
                            namespace=self.settings.temporal_namespace,
                        )
                        await client.service_client.check_health()
                return DependencyStatus.model_validate({"name": name, "ready": True})
            except Exception:
                return DependencyStatus.model_validate({"name": name, "ready": False})

        names = ["postgres", "redis", "object_storage"]
        if self.settings.temporal_enabled:
            names.append("temporal")
        return tuple(await asyncio.gather(*(check_one(n) for n in names)))

    async def close(self) -> None:
        await self.redis.aclose()
        self.storage.client.close()
        self.engine.dispose()
