"""Only documented HTTPS provider endpoints; secrets never enter our error strings."""

import asyncio
import json
import logging
import time
from typing import Any

import httpx

ENDPOINTS = frozenset(
    {
        "https://newsdata.io/api/1/latest",
        "https://gnews.io/api/v4/search",
        "https://newsapi.org/v2/everything",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        "https://www.googleapis.com/youtube/v3/search",
        "https://www.googleapis.com/youtube/v3/videos",
    }
)


class ProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("Provider request failed: " + code)


def make_http_client() -> httpx.AsyncClient:
    # httpx INFO includes query strings for providers requiring query-key auth.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return httpx.AsyncClient(
        timeout=httpx.Timeout(20, connect=5),
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "AegisNews/0.1 local-academic-demo", "Accept": "application/json"},
    )


class ProviderHttp:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        spacing: float = 2.1,
        max_bytes: int = 2 * 1024 * 1024,
        retry_delay: float = 1,
    ) -> None:
        self.client, self.spacing, self.max_bytes, self.retry_delay = (
            client,
            spacing,
            max_bytes,
            retry_delay,
        )
        self.lock = asyncio.Lock()
        self.next_at = 0.0
        self.requests = 0

    async def get(
        self, endpoint: str, params: dict[str, str | int], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if endpoint not in ENDPOINTS:
            raise ProviderError("endpoint_not_allowed")
        for attempt in range(3):
            async with self.lock:
                await asyncio.sleep(max(0, self.next_at - time.monotonic()))
                self.next_at = time.monotonic() + self.spacing
            self.requests += 1
            try:
                async with self.client.stream(
                    "GET", endpoint, params=params, headers=headers, follow_redirects=False
                ) as response:
                    if response.status_code in {401, 403, 429}:
                        raise ProviderError(
                            {
                                401: "authentication",
                                403: "permission_or_quota",
                                429: "rate_or_quota",
                            }[response.status_code]
                        )
                    if response.status_code in {500, 502, 503, 504}:
                        raise httpx.ReadTimeout("retryable upstream failure")
                    if response.status_code != 200:
                        raise ProviderError("http_" + str(response.status_code))
                    if "json" not in response.headers.get("content-type", "").lower():
                        raise ProviderError("non_json_response")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_bytes:
                            raise ProviderError("response_too_large")
                    try:
                        value = json.loads(body)
                    except (ValueError, UnicodeError):
                        raise ProviderError("invalid_json") from None
                    if not isinstance(value, dict):
                        raise ProviderError("invalid_envelope")
                    return value
            except httpx.RequestError:
                if attempt == 2:
                    raise ProviderError("transport_unavailable") from None
                await asyncio.sleep(self.retry_delay * 2**attempt)
        raise AssertionError("unreachable")
