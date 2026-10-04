"""Manual provider runs stage metadata and use the authenticated ingestion HTTP API."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from prometheus_client import CollectorRegistry, Counter

from aegis.providers.adapters import ADAPTERS
from aegis.providers.models import (
    FetchBatch,
    FetchOptions,
    ProviderName,
    ProviderOutcome,
    ProviderRun,
    ProviderStatus,
)
from aegis.providers.persistence import ProviderStore
from aegis.providers.transport import ProviderError, ProviderHttp, make_http_client
from aegis.settings import Settings


class Acquisition(Protocol):
    async def fetch(self, query: str, limit: int, country: str | None = None) -> FetchBatch: ...


class Gateway(Protocol):
    async def request(self, method: str, path: str, body: Any = None) -> dict[str, Any]: ...


class IngestionGateway:
    def __init__(self, client: httpx.AsyncClient, url: str, authorization: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("provider ingestion API must be explicit local loopback")
        self.client, self.url, self.authorization = client, url.rstrip("/"), authorization

    async def request(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        for attempt in range(3):
            try:
                response = await self.client.request(
                    method,
                    self.url + path,
                    json=body,
                    headers={"Authorization": self.authorization},
                )
                if response.is_success:
                    value: dict[str, Any] = response.json()["data"]
                    return value
                if response.status_code not in {500, 502, 503, 504}:
                    raise ProviderError("ingestion_http_" + str(response.status_code))
            except (httpx.RequestError, ValueError):
                pass
            # Source creation has no idempotency. Never retry an ambiguous POST.
            if path == "/api/v1/sources" or attempt == 2:
                raise ProviderError("ingestion_unavailable") from None
            await asyncio.sleep(2**attempt)
        raise AssertionError("unreachable")


class ProviderMetrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.counters = {
            name: Counter(
                "aegis_provider_" + name + "_total",
                "Manual provider acquisition: " + name,
                ["provider"],
                registry=registry,
            )
            for name in ("fetch", "fetch_failed", "items_received", "items_ingested", "duplicates")
        }

    def add(self, event: str, provider: str, amount: int = 1) -> None:
        self.counters[event].labels(provider).inc(amount)


class ProviderRunner:
    def __init__(
        self, settings: Settings, store: ProviderStore, metrics: ProviderMetrics | None = None
    ) -> None:
        self.settings, self.store, self.metrics = settings, store, metrics
        self.lock = asyncio.Lock()

    def key(self, provider: str) -> str:
        return (
            ""
            if provider == "gdelt"
            else getattr(self.settings, provider + "_api_key").get_secret_value()
        )

    def statuses(self) -> tuple[ProviderStatus, ...]:
        from aegis.providers.models import NAMES

        return tuple(
            ProviderStatus(provider=name, enabled=name == "gdelt" or bool(self.key(name)))
            for name in NAMES
        )

    def metric(self, event: str, provider: str, amount: int = 1) -> None:
        if self.metrics:
            self.metrics.add(event, provider, amount)

    async def execute(
        self,
        names: list[ProviderName],
        options: FetchOptions,
        gateway: Gateway,
        adapters: Mapping[str, Acquisition] | None = None,
        report: ProviderRun | None = None,
    ) -> ProviderRun:
        async with self.lock:
            report = report or ProviderRun(
                run_id=str(uuid4()), created_at=datetime.now(UTC), status="running"
            )
            await asyncio.to_thread(self.store.run, report)
            outcomes: list[ProviderOutcome] = []
            async with make_http_client() as client:
                http = ProviderHttp(client)
                for name in names:
                    if name != "gdelt" and not self.key(name):
                        outcomes.append(ProviderOutcome(provider=name, status="disabled"))
                        continue
                    self.metric("fetch", name)
                    fetched = submitted = duplicates = skipped = images = videos = requests = 0
                    request_start = http.requests
                    workflows: list[str] = []
                    try:
                        adapter = (
                            adapters[name] if adapters else ADAPTERS[name](http, self.key(name))
                        )
                        batch = await adapter.fetch(options.query, options.limit, options.country)
                        fetched, skipped, requests = (
                            len(batch.records) + len(batch.videos),
                            batch.skipped,
                            batch.requests,
                        )
                        self.metric("items_received", name, fetched)
                        if batch.videos:
                            await asyncio.to_thread(self.store.videos, list(batch.videos))
                            videos = len(batch.videos)
                        for item in batch.records:
                            try:
                                known = await asyncio.to_thread(self.store.known, item)
                                if known:
                                    source_id = known.request["source_id"]
                                else:
                                    host = urlsplit(item.article_url or "").hostname
                                    publisher = item.publisher_name or host
                                    if not publisher:
                                        skipped += 1
                                        continue
                                    publisher_url = item.publisher_url or (
                                        "https://" + host if host else None
                                    )
                                    source_id = await asyncio.to_thread(
                                        self.store.publisher, publisher, publisher_url
                                    )
                                    if not source_id:
                                        source_id = (
                                            await gateway.request(
                                                "POST",
                                                "/api/v1/sources",
                                                {
                                                    "name": publisher,
                                                    "kind": "web",
                                                    "url": publisher_url,
                                                },
                                            )
                                        )["source_id"]
                                row, duplicate = await asyncio.to_thread(
                                    self.store.prepare, item, source_id
                                )
                                if duplicate:
                                    duplicates += 1
                                    self.metric("duplicates", name)
                                retry = row.workflow_id is None or options.retry_failed
                                if retry:
                                    result = await gateway.request(
                                        "POST", "/api/v1/ingestions", row.request
                                    )
                                    await asyncio.to_thread(
                                        self.store.submitted, row.article_id, result["workflow_id"]
                                    )
                                    workflows.append(result["workflow_id"])
                                    submitted += 1
                                    self.metric("items_ingested", name)
                                else:
                                    assert row.workflow_id is not None
                                    workflows.append(row.workflow_id)
                                images += bool(
                                    item.image_url and item.image_url.startswith("https://")
                                )
                            except ValueError:
                                skipped += 1
                        outcome = ProviderOutcome(
                            provider=name,
                            status="submitted",
                            fetched=fetched,
                            submitted=submitted,
                            duplicates=duplicates,
                            skipped=skipped,
                            images=images,
                            videos=videos,
                            requests=requests,
                            workflow_ids=tuple(workflows),
                        )
                    except Exception as exc:
                        requests = http.requests - request_start
                        self.metric("fetch_failed", name)
                        # Never stringify HTTP/validation exceptions: they may carry keys.
                        error = (
                            exc.code
                            if isinstance(exc, ProviderError)
                            else "internal_acquisition_failure"
                        )
                        outcome = ProviderOutcome(
                            provider=name,
                            status="failed",
                            error=error,
                            fetched=fetched,
                            submitted=submitted,
                            duplicates=duplicates,
                            skipped=skipped,
                            images=images,
                            videos=videos,
                            requests=requests,
                            workflow_ids=tuple(workflows),
                        )
                    outcomes.append(outcome)
                    report = report.model_copy(update={"outcomes": tuple(outcomes)})
                    await asyncio.to_thread(self.store.run, report)
            report = report.model_copy(
                update={
                    "status": "submitted",
                    "completed_at": datetime.now(UTC),
                    "outcomes": tuple(outcomes),
                }
            )
            await asyncio.to_thread(self.store.run, report)
            return report
