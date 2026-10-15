"""Bounded free-source acquisition; input URLs never become request destinations."""

import asyncio
import hashlib
import html
import json
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

import httpx
from pydantic import ValidationError

from aegis.providers.adapters import GdeltProvider
from aegis.providers.models import canonical_url
from aegis.showcase.daily_contracts import MediaLink, MediaReference, MetadataV2, has_term
from aegis.showcase.sources import COMMONS_API, MEDIA_ENDPOINTS, NASA_MEDIA_API, REGISTRY


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join(html.unescape("".join(parser.parts)).split())[:512]


def timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            result = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return None
    return result.astimezone(UTC) if result.tzinfo else None


class AcquisitionError(RuntimeError):
    pass


class Fetcher:
    def __init__(self, client: httpx.AsyncClient, *, spacing: float = 6) -> None:
        self.client = client
        self.requests = 0
        self.spacing = spacing
        self.next_at = 0.0

    async def get(self, endpoint: str, params: dict[str, str | int] | None = None) -> bytes:
        if endpoint not in {s.endpoint for s in REGISTRY.values()} | set(MEDIA_ENDPOINTS):
            raise AcquisitionError("unapproved acquisition endpoint")
        for attempt in range(3):
            if self.requests >= 18:
                raise AcquisitionError("per-run request ceiling reached")
            await asyncio.sleep(max(0, self.next_at - time.monotonic()))
            self.next_at = time.monotonic() + self.spacing
            self.requests += 1
            retry = False
            delay = 30 * 2**attempt
            try:
                async with self.client.stream(
                    "GET", endpoint, params=params, follow_redirects=False
                ) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        retry = True
                        header = response.headers.get("retry-after", "")
                        retry_at = timestamp(header) if header and not header.isdigit() else None
                        requested = (
                            int(header)
                            if header.isdigit()
                            else (
                                max(0, int((retry_at - datetime.now(UTC)).total_seconds()))
                                if retry_at
                                else 0
                            )
                        )
                        if requested:
                            if requested > 120:
                                raise AcquisitionError("provider retry window exceeds run budget")
                            delay = max(delay, requested)
                    elif response.status_code != 200:
                        raise AcquisitionError("provider HTTP " + str(response.status_code))
                    else:
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 2 * 1024 * 1024:
                                raise AcquisitionError("provider response exceeds 2 MiB")
                        return bytes(body)
            except httpx.RequestError:
                retry = True
            if not retry or attempt == 2:
                raise AcquisitionError("bounded provider attempts exhausted")
            await asyncio.sleep(delay)
        raise AcquisitionError("provider unavailable")


def article(
    source: str,
    title: str,
    url: str,
    published: datetime | None,
    acquired: datetime,
    *,
    categories: tuple[str, ...] = (),
    discovered: datetime | None = None,
    publisher: str | None = None,
    country: str | None = None,
    occurred: datetime | None = None,
    updated: datetime | None = None,
) -> MetadataV2:
    identity = canonical_url(url)
    return MetadataV2(
        id=hashlib.sha256(identity.encode()).hexdigest(),
        source=source,
        source_identity=identity,
        title=text(title),
        url=url,
        publisher=publisher or REGISTRY[source].name,
        published_at=published,
        discovered_at=discovered,
        acquired_at=acquired,
        source_categories=categories,
        publisher_country=country,
        occurred_at=occurred,
        source_updated_at=updated,
    )


def parse_feed(source: str, content: bytes, acquired: datetime) -> list[MetadataV2]:
    decoded = content.decode("utf-8-sig")
    if "<!DOCTYPE" in decoded.upper() or "<!ENTITY" in decoded.upper():
        raise AcquisitionError("XML declarations are not permitted")
    root = ET.fromstring(decoded)
    result = []
    for item in root.findall("./channel/item")[: REGISTRY[source].limit]:
        try:
            published = timestamp(
                item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            )
            result.append(
                article(
                    source,
                    item.findtext("title") or "",
                    item.findtext("link") or "",
                    published,
                    acquired,
                    categories=tuple(
                        text(x.text or "")
                        for x in item.findall("category")[:12]
                        if text(x.text or "")
                    ),
                )
            )
        except (ValidationError, ValueError):
            continue
    return result


async def acquire(
    fetcher: Fetcher, now: datetime, window_days: int
) -> tuple[list[MetadataV2], dict[str, str]]:
    records: list[MetadataV2] = []
    outcomes: dict[str, str] = {}
    for source, policy in REGISTRY.items():
        try:
            if policy.kind == "usgs":
                value = json.loads(await fetcher.get(policy.endpoint))
                captured = datetime.now(UTC)
                rows = []
                for item in value.get("features", [])[: policy.limit]:
                    properties = item.get("properties", {})
                    try:
                        rows.append(
                            article(
                                source,
                                properties["title"],
                                properties["url"],
                                None,
                                captured,
                                updated=datetime.fromtimestamp(properties["updated"] / 1000, UTC),
                                occurred=datetime.fromtimestamp(properties["time"] / 1000, UTC),
                            )
                        )
                    except (KeyError, ValueError, TypeError, ValidationError):
                        continue
            elif policy.kind == "gdelt":
                body = await fetcher.get(
                    policy.endpoint,
                    {
                        "query": (
                            "(government OR economy OR technology OR health OR climate OR science) "
                            "sourcelang:english"
                        ),
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": policy.limit,
                        "timespan": str(window_days) + "d",
                        "sort": "datedesc",
                    },
                )
                captured = datetime.now(UTC)
                adapter = GdeltProvider(None)  # type: ignore[arg-type]
                rows = []
                for raw in json.loads(body).get("articles", [])[: policy.limit]:
                    try:
                        normalized = adapter.normalize(raw)
                        if normalized.article_url:
                            rows.append(
                                article(
                                    source,
                                    normalized.title,
                                    normalized.article_url,
                                    None,
                                    captured,
                                    discovered=normalized.discovered_at,
                                    publisher=normalized.publisher_name,
                                    country=text(str(raw.get("sourcecountry", ""))) or None,
                                )
                            )
                    except (ValidationError, ValueError, TypeError, KeyError):
                        continue
            else:
                payload = await fetcher.get(policy.endpoint)
                rows = parse_feed(source, payload, datetime.now(UTC))
            recent = [
                r
                for r in rows
                if (r.published_at or r.discovered_at or r.source_updated_at) is not None
                and (r.published_at or r.discovered_at or r.source_updated_at or now)
                >= now - timedelta(days=window_days)
            ]
            records.extend(recent)
            outcomes[source] = f"{len(recent)} recent permitted records"
        except (AcquisitionError, ValueError, TypeError, KeyError, AttributeError, ET.ParseError):
            outcomes[source] = "unavailable; previous valid records retained"
    return records, outcomes


async def media(fetcher: Fetcher, headlines: dict[str, str], now: datetime) -> list[MediaLink]:
    term = next(
        (
            word
            for word in ("Artemis", "Mars", "Moon")
            if any(has_term(word, title) for title in headlines.values())
        ),
        None,
    )
    if term is None:
        return []
    ids = tuple(sorted(k for k, title in headlines.items() if has_term(term, title)))[:12]
    result = []
    try:
        value = json.loads(
            await fetcher.get(
                COMMONS_API,
                {
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": term + " NASA",
                    "gsrnamespace": 6,
                    "gsrlimit": 3,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata",
                    "iiurlwidth": 720,
                },
            )
        )
        captured = datetime.now(UTC)
        for page in value.get("query", {}).get("pages", {}).values():
            info = page.get("imageinfo", [{}])[0]
            meta = info.get("extmetadata", {})

            def field(key: str, values: dict[str, Any] = meta) -> str:
                return str(values.get(key, {}).get("value", ""))

            licenses = {
                "CC BY 4.0": "CC BY 4.0",
                "CC BY-SA 4.0": "CC BY-SA 4.0",
                "CC0": "CC0",
                "Public domain": "Public Domain",
            }
            license_name = licenses.get(field("LicenseShortName"))
            if not license_name or not field("Artist"):
                continue
            source_url = info.get("descriptionurl", "")
            license_url = field("LicenseUrl")
            if license_url.startswith("http://creativecommons.org/"):
                license_url = "https://" + license_url.removeprefix("http://")
            if license_name == "Public Domain":
                if field("Copyrighted").casefold() != "false":
                    continue
                license_url = source_url + "#Licensing"
            title = text(page.get("title", "").removeprefix("File:"))
            try:
                reference = MediaReference.model_validate(
                    {
                        "id": hashlib.sha256(source_url.encode()).hexdigest(),
                        "kind": "image",
                        "title": title,
                        "source_url": source_url,
                        "asset_url": info.get("thumburl"),
                        "creator": text(field("Artist")),
                        "license": license_name,
                        "license_url": license_url,
                        "alt": title,
                        "relationship_term": term,
                        "acquired_at": captured,
                        "refreshed_at": captured,
                        "platform_id": str(page["pageid"]),
                        "publisher": "Wikimedia Commons",
                    }
                )
                result.append(MediaLink(reference=reference, record_ids=ids))
            except (ValidationError, ValueError):
                continue
    except (AcquisitionError, ValueError, TypeError, KeyError, IndexError, AttributeError):
        pass
    try:
        value = json.loads(
            await fetcher.get(
                NASA_MEDIA_API,
                {
                    "q": term,
                    "media_type": "video",
                    "year_start": now.year,
                    "page_size": 3,
                },
            )
        )
        captured = datetime.now(UTC)
        for item in value.get("collection", {}).get("items", [])[:3]:
            data = item.get("data", [{}])[0]
            title = text(data.get("title", ""))
            identity = str(data.get("nasa_id", ""))
            from urllib.parse import quote

            url = "https://images.nasa.gov/details/" + quote(identity, safe="")
            try:
                reference = MediaReference.model_validate(
                    {
                        "id": hashlib.sha256(url.encode()).hexdigest(),
                        "kind": "video",
                        "title": title,
                        "source_url": url,
                        "creator": "NASA",
                        "license": "NASA Reference Only",
                        "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                        "alt": title,
                        "relationship_term": term,
                        "acquired_at": captured,
                        "refreshed_at": captured,
                        "created_at": timestamp(data.get("date_created")),
                        "platform_id": identity,
                        "publisher": "NASA Image and Video Library",
                    }
                )
                result.append(MediaLink(reference=reference, record_ids=ids))
            except (ValidationError, ValueError):
                continue
    except (AcquisitionError, ValueError, TypeError, KeyError, IndexError, AttributeError):
        pass
    return result
