"""Synthetic provider fixtures only; normal CI never contacts upstream APIs."""

import json

import httpx
import pytest

from aegis.providers.adapters import (
    GdeltProvider,
    GNewsProvider,
    NewsApiProvider,
    NewsDataProvider,
    YouTubeProvider,
)
from aegis.providers.models import ExternalNewsRecord, canonical_url, safe_url
from aegis.providers.transport import ProviderError, ProviderHttp
from aegis.settings import Settings

FIXTURES = {
    "newsdata": {
        "status": "success",
        "results": [
            {
                "article_id": "one",
                "title": "Atlas launches technology",
                "description": "An original synthetic description.",
                "link": "https://publisher.test/a",
                "source_name": "Publisher",
                "source_url": "https://publisher.test",
                "language": "english",
                "pubDate": "2026-10-01 10:00:00",
                "pubDateTZ": "UTC",
                "image_url": "https://images.test/a.jpg",
                "category": ["technology"],
            }
        ],
        "nextPage": "next",
    },
    "gnews": {
        "totalArticles": 2,
        "articles": [
            {
                "id": "one",
                "title": "Atlas launches technology",
                "description": "An original synthetic description.",
                "url": "https://publisher.test/a",
                "source": {"name": "Publisher", "url": "https://publisher.test"},
                "publishedAt": "2026-10-01T10:00:00Z",
                "image": "https://images.test/a.jpg",
                "lang": "en",
            }
        ],
    },
    "newsapi": {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "title": "Atlas launches technology",
                "description": "An original synthetic description.",
                "url": "https://publisher.test/a",
                "source": {"name": "Publisher", "id": None},
                "publishedAt": "2026-10-01T10:00:00Z",
                "urlToImage": "https://images.test/a.jpg",
                "author": None,
            }
        ],
    },
    "gdelt": {
        "articles": [
            {
                "title": "Atlas launches technology",
                "url": "https://publisher.test/a",
                "domain": "publisher.test",
                "language": "English",
                "seendate": "20261001T100000Z",
                "socialimage": "https://images.test/a.jpg",
            }
        ]
    },
    "youtube": {
        "items": [
            {
                "id": {"videoId": "abcdefghijk"},
                "snippet": {
                    "title": "Technology news",
                    "channelId": "channel-one",
                    "channelTitle": "News channel",
                    "publishedAt": "2026-10-01T10:00:00Z",
                    "thumbnails": {
                        "medium": {"url": "https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg"}
                    },
                },
            }
        ],
        "nextPageToken": "next",
    },
}


@pytest.mark.parametrize(
    "name,adapter",
    [
        ("newsdata", NewsDataProvider),
        ("gnews", GNewsProvider),
        ("newsapi", NewsApiProvider),
        ("gdelt", GdeltProvider),
        ("youtube", YouTubeProvider),
    ],
)
async def test_success_auth_and_bounded_pagination(name, adapter):
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/videos"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "abcdefghijk", "snippet": FIXTURES["youtube"]["items"][0]["snippet"]}
                    ]
                },
            )
        fixture = {**FIXTURES[name]}
        if name == "gnews":
            fixture["totalArticles"] = 20
        if name == "newsapi":
            fixture["totalResults"] = 20
        return httpx.Response(200, json=fixture)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await adapter(ProviderHttp(client, spacing=0), "test-secret").fetch(
            "technology", 2
        )
    assert len(result.records if name != "youtube" else result.videos) >= 1
    assert len(requests) <= 3
    first = requests[0]
    if name == "newsdata":
        assert first.headers["X-ACCESS-KEY"] == "test-secret"
        assert requests[1].url.params["page"] == "next"
    elif name == "newsapi":
        assert first.headers["X-Api-Key"] == "test-secret"
        assert requests[1].url.params["page"] == "2"
    elif name == "gnews":
        assert first.url.params["apikey"] == "test-secret"
        assert requests[1].url.params["page"] == "2"
    elif name == "youtube":
        assert first.url.params["key"] == "test-secret"
    else:
        assert "test-secret" not in str(first.url)
        assert result.records[0].published_at is None  # discovery is not publication
    if name != "youtube":
        record = result.records[0]
        assert record.publisher_name in {"Publisher", "publisher.test"}
        assert record.image_url == "https://images.test/a.jpg"
        assert record.language == "en"


@pytest.mark.parametrize(
    "adapter", [NewsDataProvider, GNewsProvider, NewsApiProvider, GdeltProvider, YouTubeProvider]
)
async def test_missing_optional_fields_never_fabricated(adapter):
    name = adapter.name
    fixture = json.loads(json.dumps(FIXTURES[name]))
    if name == "youtube":
        fixture["items"][0]["snippet"].pop("thumbnails")
    else:
        rows = fixture.get("results", fixture.get("articles"))
        for key in (
            "image_url",
            "image",
            "urlToImage",
            "socialimage",
            "author",
            "creator",
            "publishedAt",
            "pubDate",
            "seendate",
        ):
            rows[0].pop(key, None)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=fixture))
    ) as client:
        result = await adapter(ProviderHttp(client, spacing=0), "test-secret").fetch("news", 1)
    if name != "youtube":
        assert result.records[0].image_url is None
        assert result.records[0].author is None
        assert result.records[0].published_at is None


@pytest.mark.parametrize("status", [401, 403, 429])
async def test_nonretryable_failures_redact_request_and_response(status):
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"message": "test-secret", "url": str(request.url)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderError) as exc:
            await ProviderHttp(client, spacing=0).get(
                "https://gnews.io/api/v4/search", {"apikey": "test-secret"}
            )
    assert calls == 1
    assert "test-secret" not in str(exc.value)


@pytest.mark.parametrize("failure", ["timeout", "bad_json", "oversize", "redirect", "html"])
async def test_transport_bounds_and_sanitized_errors(failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("test-secret", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1"})
        if failure == "oversize":
            return httpx.Response(
                200, content=b"x" * 300, headers={"content-type": "application/json"}
            )
        if failure == "html":
            return httpx.Response(200, text="test-secret", headers={"content-type": "text/html"})
        return httpx.Response(
            200, content=b"{test-secret", headers={"content-type": "application/json"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderError) as exc:
            await ProviderHttp(client, spacing=0, max_bytes=100, retry_delay=0).get(
                "https://gnews.io/api/v4/search", {}
            )
    assert "test-secret" not in str(exc.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a",
        "https://localhost/a",
        "https://169.254.169.254/a",
        "https://user:secret@publisher.test/a",
        "javascript:alert(1)",
        "https://foo.local/a",
    ],
)
def test_unsafe_external_references_rejected(url):
    assert safe_url(url) is None


def test_dedupe_url_and_headline_identities_and_secret_settings():
    assert (
        canonical_url("https://Publisher.test/a?utm_source=x&b=2&a=1#frag")
        == "https://publisher.test/a?a=1&b=2"
    )
    record = ExternalNewsRecord(
        provider="gnews",
        provider_item_id="one",
        title="Atlas:  news!",
        article_url="https://publisher.test/a",
    )
    other = record.model_copy(
        update={"provider": "newsapi", "provider_item_id": "two", "title": "ATLAS news"}
    )
    assert record.aliases()[1:] == other.aliases()[1:]
    assert record.article().text == record.title
    settings = Settings(_env_file=None, gnews_api_key="test-secret")
    assert "test-secret" not in repr(settings)


async def test_unapproved_endpoint_never_requested():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: pytest.fail("SSRF request"))
    ) as client:
        with pytest.raises(ProviderError):
            await ProviderHttp(client).get("https://gnews.io/redirect", {})
