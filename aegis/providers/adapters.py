"""Current documented contracts. Never scrape linked publishers or download media."""

import html
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from aegis.providers.models import (
    ExternalNewsRecord,
    FetchBatch,
    ProviderName,
    YouTubeReference,
    safe_url,
)
from aegis.providers.transport import ProviderError, ProviderHttp


def text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return html.unescape(value.strip())
    return None


def date(value: object, timezone: object = None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None and isinstance(timezone, str):
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (ValueError, ZoneInfoNotFoundError):
        return None


class ArticleProvider:
    name: ProviderName
    endpoint: str
    rows_key = "articles"

    def __init__(self, http: ProviderHttp, key: str = "") -> None:
        self.http, self.key = http, key

    def parameters(
        self, query: str, limit: int, country: str | None
    ) -> tuple[dict[str, str | int], dict[str, str]]:
        raise NotImplementedError

    def normalize(self, row: dict[str, Any]) -> ExternalNewsRecord:
        raise NotImplementedError

    async def fetch(self, query: str, limit: int, country: str | None = None) -> FetchBatch:
        if not 1 <= limit <= 30:
            raise ProviderError("invalid_limit")
        if self.name != "gdelt" and not self.key:
            raise ProviderError("disabled")
        params, headers = self.parameters(query, limit, country)
        records: list[ExternalNewsRecord] = []
        skipped = 0
        initial = self.http.requests
        visited: set[str] = set()
        for page in range(1, 4):
            value = await self.http.get(self.endpoint, params, headers)
            if value.get("status") in {"error", "fail"}:
                raise ProviderError("provider_rejected_request")
            rows = value.get(self.rows_key)
            if not isinstance(rows, list):
                raise ProviderError("invalid_items")
            for row in rows:
                try:
                    if not isinstance(row, dict):
                        raise ValueError
                    records.append(self.normalize(row))
                except (ValidationError, ValueError, TypeError, AttributeError):
                    skipped += 1
                if len(records) >= limit:
                    break
            if len(records) >= limit or not rows or self.name == "gdelt":
                break
            if self.name == "newsdata":
                cursor = value.get("nextPage")
                if not isinstance(cursor, str) or not cursor or cursor in visited:
                    break
                visited.add(cursor)
                params["page"] = cursor
            else:
                total = value.get("totalArticles", value.get("totalResults", 0))
                if (
                    not isinstance(total, int)
                    or page * int(params.get("max", params.get("pageSize", 10))) >= total
                ):
                    break
                params["page"] = page + 1
        return FetchBatch(
            records=tuple(records), skipped=skipped, requests=self.http.requests - initial
        )


class NewsDataProvider(ArticleProvider):
    name: ProviderName = "newsdata"
    endpoint = "https://newsdata.io/api/1/latest"
    rows_key = "results"

    def parameters(
        self, query: str, limit: int, country: str | None
    ) -> tuple[dict[str, str | int], dict[str, str]]:
        params: dict[str, str | int] = {"q": query, "language": "en", "size": min(limit, 10)}
        if country:
            params["country"] = country
        return params, {"X-ACCESS-KEY": self.key}

    def normalize(self, row: dict[str, Any]) -> ExternalNewsRecord:
        creators = row.get("creator")
        categories = row.get("category")
        return ExternalNewsRecord(
            provider=self.name,
            provider_item_id=text(row.get("article_id")),
            title=text(row.get("title")) or "",
            description=text(row.get("description")),
            body=None,
            language="en" if row.get("language") in {"english", "en"} else None,
            article_url=text(row.get("link")),
            publisher_name=text(row.get("source_name")),
            publisher_url=text(row.get("source_url")),
            author=", ".join(c for c in creators if isinstance(c, str))
            if isinstance(creators, list)
            else None,
            published_at=date(row.get("pubDate"), row.get("pubDateTZ")),
            image_url=text(row.get("image_url")),
            video_url=text(row.get("video_url")),
            provider_category=tuple(c for c in categories if isinstance(c, str))
            if isinstance(categories, list)
            else (),
        )


class GNewsProvider(ArticleProvider):
    name: ProviderName = "gnews"
    endpoint = "https://gnews.io/api/v4/search"

    def parameters(
        self, query: str, limit: int, country: str | None
    ) -> tuple[dict[str, str | int], dict[str, str]]:
        params: dict[str, str | int] = {
            "q": query,
            "lang": "en",
            "max": min(limit, 10),
            "page": 1,
            "apikey": self.key,
            "nullable": "description,content,image",
        }
        if country:
            params["country"] = country
        return params, {}

    def normalize(self, row: dict[str, Any]) -> ExternalNewsRecord:
        source = row.get("source") or {}
        return ExternalNewsRecord(
            provider=self.name,
            provider_item_id=text(row.get("id")),
            title=text(row.get("title")) or "",
            description=text(row.get("description")),
            body=None,
            language=text(row.get("lang")),
            published_at=date(row.get("publishedAt")),
            article_url=text(row.get("url")),
            publisher_name=text(source.get("name")),
            publisher_url=text(source.get("url")),
            image_url=text(row.get("image")),
        )


class NewsApiProvider(ArticleProvider):
    name: ProviderName = "newsapi"
    endpoint = "https://newsapi.org/v2/everything"

    def parameters(
        self, query: str, limit: int, country: str | None
    ) -> tuple[dict[str, str | int], dict[str, str]]:
        # /everything has no country filter. Geography belongs in an honest query.
        return {
            "q": query
            + (" India" if country == "in" else " United States" if country == "us" else ""),
            "language": "en",
            "pageSize": min(limit, 10),
            "page": 1,
            "sortBy": "publishedAt",
        }, {"X-Api-Key": self.key}

    def normalize(self, row: dict[str, Any]) -> ExternalNewsRecord:
        source = row.get("source") or {}
        url = safe_url(row.get("url"), https_only=False)
        return ExternalNewsRecord(
            provider=self.name,
            title=text(row.get("title")) or "",
            description=text(row.get("description")),
            body=None,
            language="en",
            published_at=date(row.get("publishedAt")),
            article_url=url,
            publisher_name=text(source.get("name")),
            publisher_url=("https://" + urlsplit(url).netloc) if url else None,
            image_url=text(row.get("urlToImage")),
            author=text(row.get("author")),
        )


class GdeltProvider(ArticleProvider):
    name: ProviderName = "gdelt"
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"

    def parameters(
        self, query: str, limit: int, country: str | None
    ) -> tuple[dict[str, str | int], dict[str, str]]:
        # Boolean OR groups must be parenthesized in DOC queries.
        if " OR " in query:
            query = "(" + query + ")"
        query = (
            query
            + " sourcelang:english"
            + (
                " sourcecountry:IN"
                if country == "in"
                else " sourcecountry:US"
                if country == "us"
                else ""
            )
        )
        return {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max(5, limit),
            "timespan": "3d",
            "sort": "datedesc",
        }, {}

    def normalize(self, row: dict[str, Any]) -> ExternalNewsRecord:
        url = safe_url(row.get("url"), https_only=False)
        return ExternalNewsRecord(
            provider=self.name,
            title=text(row.get("title")) or "",
            language="en" if row.get("language") in {"English", "english", "en"} else None,
            article_url=url,
            publisher_name=text(row.get("domain")),
            publisher_url=("https://" + urlsplit(url).netloc) if url else None,
            image_url=text(row.get("socialimage")),
            discovered_at=date(row.get("seendate")),
        )


class YouTubeProvider:
    name: ProviderName = "youtube"

    def __init__(self, http: ProviderHttp, key: str = "") -> None:
        self.http, self.key = http, key

    def reference(self, video_id: str, snippet: dict[str, Any]) -> YouTubeReference:
        now = datetime.now(UTC)
        thumbs = snippet.get("thumbnails") or {}
        image = (thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        thumbnail = safe_url(image)
        if thumbnail and urlsplit(thumbnail).hostname not in {
            "i.ytimg.com",
            "i1.ytimg.com",
            "i2.ytimg.com",
            "i3.ytimg.com",
            "i4.ytimg.com",
        }:
            thumbnail = None
        return YouTubeReference(
            video_id=video_id,
            title=text(snippet.get("title")) or "",
            channel_id=text(snippet.get("channelId")) or "",
            channel_title=text(snippet.get("channelTitle")) or "",
            published_at=date(snippet.get("publishedAt")),
            thumbnail_url=thumbnail,
            youtube_url="https://www.youtube.com/watch?v=" + video_id,
            last_refreshed_at=now,
            expires_at=now + timedelta(days=29),
        )

    async def refresh(self, ids: list[str]) -> tuple[YouTubeReference, ...]:
        if not self.key:
            raise ProviderError("disabled")
        if not ids:
            return ()
        value = await self.http.get(
            "https://www.googleapis.com/youtube/v3/videos",
            {"part": "snippet", "id": ",".join(ids[:50]), "key": self.key},
        )
        rows = value.get("items")
        if not isinstance(rows, list):
            raise ProviderError("invalid_items")
        results = []
        for row in rows:
            try:
                results.append(self.reference(row["id"], row["snippet"]))
            except (ValidationError, KeyError, TypeError):
                continue
        return tuple(results)

    async def fetch(self, query: str, limit: int, country: str | None = None) -> FetchBatch:
        if not self.key:
            raise ProviderError("disabled")
        initial = self.http.requests
        limit = min(limit, 10)
        params: dict[str, str | int] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": limit,
            "relevanceLanguage": "en",
            "videoEmbeddable": "true",
            "key": self.key,
        }
        if country:
            params["regionCode"] = country.upper()
        ids = []
        for _ in range(2):
            value = await self.http.get("https://www.googleapis.com/youtube/v3/search", params)
            rows = value.get("items")
            if not isinstance(rows, list):
                raise ProviderError("invalid_items")
            for row in rows:
                identity = row.get("id", {}).get("videoId") if isinstance(row, dict) else None
                if isinstance(identity, str) and identity not in ids:
                    ids.append(identity)
            cursor = value.get("nextPageToken")
            if len(ids) >= limit or not cursor or params.get("pageToken") == cursor:
                break
            params["pageToken"] = str(cursor)
        videos = await self.refresh(ids[:limit])
        return FetchBatch(
            videos=videos,
            skipped=len(ids[:limit]) - len(videos),
            requests=self.http.requests - initial,
        )


ADAPTERS: dict[str, type[ArticleProvider] | type[YouTubeProvider]] = {
    "newsdata": NewsDataProvider,
    "gnews": GNewsProvider,
    "newsapi": NewsApiProvider,
    "gdelt": GdeltProvider,
    "youtube": YouTubeProvider,
}
