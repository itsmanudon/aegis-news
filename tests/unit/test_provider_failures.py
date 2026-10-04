"""Every adapter shares bounded failures; no external calls or credential snapshots."""

import httpx
import pytest

from aegis.providers.adapters import ADAPTERS
from aegis.providers.transport import ProviderError, ProviderHttp


@pytest.mark.parametrize("adapter", list(ADAPTERS.values()))
@pytest.mark.parametrize("failure", [401, 403, 429, "timeout", "bad_json"])
async def test_adapter_failure_is_sanitized_and_nonretryable_statuses_stop(adapter, failure):
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic-credential", request=request)
        if failure == "bad_json":
            return httpx.Response(
                200, content=b"{synthetic-credential", headers={"content-type": "application/json"}
            )
        return httpx.Response(failure, json={"error": "synthetic-credential"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderError) as error:
            await adapter(
                ProviderHttp(client, spacing=0, retry_delay=0), "synthetic-credential"
            ).fetch("technology", 1)
    assert "synthetic-credential" not in str(error.value)
    assert calls == (3 if failure == "timeout" else 1)


async def test_temporary_server_error_retries_only_with_bounded_attempts():
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls < 3 else 200, json={"articles": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await ADAPTERS["gdelt"](ProviderHttp(client, spacing=0, retry_delay=0)).fetch(
            "technology", 3
        )
    assert calls == 3 and not result.records
