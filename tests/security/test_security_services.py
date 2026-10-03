import hashlib
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from aegis.persistence.database import make_engine
from aegis.security.abuse import RedisRateLimiter
from aegis.security.audit import AuditLog
from aegis.security.persistence import SQLAuditSink
from aegis.settings import Settings


@pytest.mark.integration
async def test_redis_rate_limiter_atomic_window():
    redis = Redis.from_url(Settings().redis_url.get_secret_value())
    identity = "synthetic-test:" + uuid4().hex
    key = "aegis:rate:" + hashlib.sha256(identity.encode()).hexdigest()
    try:
        import asyncio

        limiter = RedisRateLimiter(redis, 5)
        results = await asyncio.gather(*(limiter.allow(identity) for _ in range(20)))
        assert sum(results) == 5
        assert 0 < await redis.ttl(key) <= 60
    finally:
        await redis.delete(key)
        await redis.aclose()


@pytest.mark.integration
@pytest.mark.database
def test_postgres_security_tables_are_append_only():
    engine = make_engine(Settings())
    try:
        sink = SQLAuditSink(engine)
        AuditLog(sink).emit("security_change", actor="synthetic-test", outcome="success")
        assert sink.recent(1)[0].action == "security_change"
        for statement in [
            "UPDATE audit_events SET action=action WHERE false",
            "DELETE FROM audit_events WHERE false",
            "UPDATE signed_manifests SET key_id=key_id WHERE false",
            "DELETE FROM signed_manifests WHERE false",
        ]:
            with pytest.raises(DBAPIError), engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()
