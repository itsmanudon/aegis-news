"""Normalized acquisition metadata, separate from canonical intelligence contracts."""

import hashlib
import ipaddress
import re
import unicodedata
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from aegis.normalization.article import Article

ProviderName = Literal["newsdata", "gnews", "newsapi", "gdelt", "youtube"]
NAMES: tuple[ProviderName, ...] = ("newsdata", "gnews", "newsapi", "gdelt", "youtube")


def safe_url(value: object, *, https_only: bool = True) -> str | None:
    if not isinstance(value, str) or len(value) > 4096:
        return None
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
        if (
            parts.scheme not in ({"https"} if https_only else {"http", "https"})
            or parts.username
            or parts.password
            or parts.port not in {None, 80, 443}
            or not host
            or "." not in host
            or host.endswith((".local", ".localhost", ".internal"))
            or any(ord(c) < 33 for c in value)
            or any(
                k.lower() in {"apikey", "api_key", "access_token", "key", "token"}
                for k, _ in parse_qsl(parts.query)
            )
        ):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if re.fullmatch(r"[0-9.]+", host):
                return None
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    except ValueError:
        return None


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    )
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), "")
    )


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class ExternalNewsRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: ProviderName
    provider_item_id: str | None = Field(default=None, max_length=512)
    publisher_name: str | None = Field(default=None, max_length=512)
    publisher_url: str | None = None
    article_url: str | None = None
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=65536)
    body: str | None = Field(default=None, max_length=131072)
    language: str | None = None
    published_at: AwareDatetime | None = None
    author: str | None = Field(default=None, max_length=512)
    image_url: str | None = None
    video_url: str | None = None
    provider_category: tuple[str, ...] = ()
    discovered_at: AwareDatetime | None = None

    @field_validator("article_url", "publisher_url", "image_url", "video_url")
    @classmethod
    def public_reference(cls, value: str | None) -> str | None:
        return safe_url(value, https_only=False) if value else None

    @field_validator("title")
    @classmethod
    def meaningful(cls, value: str) -> str:
        value = value.strip()
        if not value or "\x00" in value:
            raise ValueError("invalid headline")
        return value

    def aliases(self) -> list[str]:
        values = []
        if self.provider_item_id:
            values.append("item:" + self.provider + ":" + hash_value(self.provider_item_id))
        if self.article_url:
            values.append("url:" + hash_value(canonical_url(self.article_url)))
        headline = " ".join(
            re.findall(r"\w+", unicodedata.normalize("NFKC", self.title).casefold())
        )
        # Exact normalized headline, not fuzzy clustering. Generic/short headlines
        # must not merge unrelated articles across publishers.
        if len(headline) >= 10:
            values.append("headline:" + hash_value(headline))
        if not values:
            values.append("item:" + self.provider + ":" + hash_value(self.title))
        return values

    def article(self) -> Article:
        text = self.body or self.description or self.title
        return Article(
            title=self.title, text=text, language=self.language, published_at=self.published_at
        )


class YouTubeReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    title: str = Field(min_length=1, max_length=512)
    channel_id: str = Field(min_length=1, max_length=128)
    channel_title: str = Field(max_length=512)
    published_at: AwareDatetime | None = None
    thumbnail_url: str | None = None
    youtube_url: str
    last_refreshed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: AwareDatetime


class FetchBatch(BaseModel):
    records: tuple[ExternalNewsRecord, ...] = ()
    videos: tuple[YouTubeReference, ...] = ()
    skipped: int = 0
    requests: int = 0


class FetchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="technology", min_length=2, max_length=100)
    limit: int = Field(default=3, ge=1, le=30)
    country: Literal["in", "us"] | None = None
    retry_failed: bool = False


class ProviderStatus(BaseModel):
    provider: ProviderName
    enabled: bool
    mode: str = "manual local development"


class ProviderOutcome(BaseModel):
    provider: ProviderName
    status: Literal["submitted", "disabled", "failed"]
    fetched: int = 0
    submitted: int = 0
    duplicates: int = 0
    skipped: int = 0
    images: int = 0
    videos: int = 0
    requests: int = 0
    error: str | None = None
    workflow_ids: tuple[str, ...] = ()


class ProviderRun(BaseModel):
    run_id: str
    created_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    status: Literal["running", "submitted", "interrupted"]
    outcomes: tuple[ProviderOutcome, ...] = ()
    workflow_statuses: dict[str, str] = {}


class ArticleEvidence(BaseModel):
    provider: ProviderName
    provider_item_id: str | None = None
    publisher_name: str | None = None
    article_url: str | None = None
    author: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    acquired_at: AwareDatetime
    content_kind: Literal["provider excerpt", "headline only"]


class ProviderArticleView(BaseModel):
    article_id: str
    acquired_at: AwareDatetime
    document_id: str | None = None
    title: str
    source_id: str
    published_at: AwareDatetime | None = None
    workflow_id: str | None = None
    evidence: tuple[ArticleEvidence, ...] = ()
