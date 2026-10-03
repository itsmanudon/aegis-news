"""Small application abuse controls. Redis windows are atomic across API workers."""

import hashlib
from collections import OrderedDict
from collections.abc import Awaitable
from threading import Lock
from time import monotonic
from typing import Any, Protocol, cast

from redis.asyncio import Redis


class RateLimiter(Protocol):
    async def allow(self, identity: str) -> bool: ...


class MemoryRateLimiter:
    """Bounded development adapter; not suitable for multiple production workers."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.windows: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self.lock = Lock()

    async def allow(self, identity: str) -> bool:
        key = hashlib.sha256(identity.encode()).hexdigest()
        with self.lock:
            now = monotonic()
            start, count = self.windows.get(key, (now, 0))
            if now - start >= 60:
                start, count = now, 0
            self.windows[key] = (start, count + 1)
            self.windows.move_to_end(key)
            if len(self.windows) > 10000:
                self.windows.popitem(last=False)
            return count < self.limit


class RedisRateLimiter:
    SCRIPT = """
    local n = redis.call('INCR', KEYS[1])
    if n == 1 then redis.call('EXPIRE', KEYS[1], 60) end
    return n
    """

    def __init__(self, redis: Redis, limit: int) -> None:
        self.redis, self.limit = redis, limit

    async def allow(self, identity: str) -> bool:
        key = "aegis:rate:" + hashlib.sha256(identity.encode()).hexdigest()
        result = await cast(Awaitable[Any], self.redis.eval(self.SCRIPT, 1, key))
        return int(result) <= self.limit
