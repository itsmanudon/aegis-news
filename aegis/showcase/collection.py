"""Manually invoked, bounded acquisition of official NASA headline metadata only."""

import base64
import hashlib
import html
import json
import subprocess
import xml.etree.ElementTree as ET
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
from cryptography.hazmat.primitives import serialization

from aegis.domain.ids import new_id
from aegis.domain.models import NewsDocument, ProvenanceRecord
from aegis.ingestion.inputs import IngestionRequest, decode_content
from aegis.intelligence.engine import build_engine
from aegis.intelligence.errors import NoPredictions
from aegis.intelligence.runtime import BaselineRuntime
from aegis.normalization.article import Article, parse_article
from aegis.provenance.service import ProvenanceService, canonical
from aegis.providers.models import canonical_url
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.keys import FileKeyProvider, generate_development_keys
from aegis.showcase.contracts import SOURCES, Metadata, PublicExport, PublicRecord


def metadata(source: str, title: str, url: str, published: datetime | None) -> Metadata:
    identity = canonical_url(url)
    return Metadata.model_validate(
        {
            "id": hashlib.sha256(identity.encode()).hexdigest(),
            "source": source,
            "source_identity": identity,
            "title": html.unescape(title).strip(),
            "url": url,
            "published_at": published,
            "acquired_at": datetime.now(UTC),
        }
    )


async def collect(
    source: str, limit: int, after: datetime | None, before: datetime | None
) -> list[Metadata]:
    if source not in SOURCES or not 1 <= limit <= 100:
        raise ValueError("unsupported source or collection limit")
    if after or before:
        if (
            source != "nasa"
            or not after
            or not before
            or after.tzinfo is None
            or before.tzinfo is None
            or not timedelta(0) < before - after <= timedelta(days=31)
            or before > datetime.now(UTC)
        ):
            raise ValueError("backfill requires NASA, past UTC dates and a 1–31 day window")
        endpoint = "https://www.nasa.gov/wp-json/wp/v2/press-release"
        params: dict[str, str | int] = {
            "after": after.isoformat(),
            "before": before.isoformat(),
            "per_page": limit,
            "_fields": "title,link,date_gmt",
        }
    else:
        endpoint, params = SOURCES[source], {}
    async with (
        httpx.AsyncClient(
            timeout=30,
            follow_redirects=False,
            headers={"User-Agent": "AegisNews/0.1 manual-academic-metadata-collection"},
        ) as client,
        client.stream("GET", endpoint, params=params) as response,
    ):
        response.raise_for_status()
        expected_type = "json" if after else "xml"
        if expected_type not in response.headers.get("content-type", ""):
            raise ValueError("source did not return the expected feed format")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > 2 * 1024 * 1024:
                raise ValueError("source response exceeds collection limit")
    rows = []
    if after:
        for value in json.loads(body):
            rows.append(
                metadata(
                    source,
                    value["title"]["rendered"],
                    value["link"],
                    datetime.fromisoformat(value["date_gmt"]).replace(tzinfo=UTC),
                )
            )
    else:
        # Only title, URL and publication date are retained. Feed bodies, excerpts,
        # images and third-party media never cross the collection boundary.
        if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
            raise ValueError("feed declarations are not allowed")
        for item in ET.fromstring(body).findall("./channel/item")[:limit]:
            date = item.findtext("pubDate")
            rows.append(
                metadata(
                    source,
                    item.findtext("title") or "",
                    item.findtext("link") or "",
                    parsedate_to_datetime(date) if date else None,
                )
            )
    if not rows:
        raise ValueError("source returned no genuine news metadata")
    return rows


def save_collection(path: Path, records: list[Metadata]) -> int:
    existing = (
        [Metadata.model_validate(r) for r in json.loads(path.read_bytes())] if path.exists() else []
    )
    unique = {r.id: r for r in existing}
    # Preserve first acquisition timestamp and original headline on duplicate refreshes.
    for record in records:
        unique.setdefault(record.id, record)
    if len(unique) > 100:
        raise ValueError("curate at most 100 records in one public release")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical([unique[key].model_dump(mode="json") for key in sorted(unique)]))
    return len(unique)


async def process(record: Metadata, keys: FileKeyProvider) -> PublicRecord:
    article = Article(title=record.title, text=record.title, published_at=record.published_at)
    request = IngestionRequest(
        source_id="src_" + str(uuid5(NAMESPACE_URL, SOURCES[record.source])),
        idempotency_key=record.id,
        content_type="application/json",
        content_base64=base64.b64encode(canonical(article.model_dump(mode="json"))).decode(),
        source_url=record.url,
        published_at=record.published_at,
        first_seen_at=record.acquired_at,
    )
    normalized = parse_article(decode_content(request), request.content_type)
    now = datetime.now(UTC)
    document = NewsDocument(
        document_id=record.document_id,
        ingestion_id=new_id("ing"),
        source_id=request.source_id,
        title=normalized.title,
        text=normalized.text,
        published_at=normalized.published_at,
        first_seen_at=record.acquired_at,
        ingested_at=now,
        created_at=now,
    )
    engine = build_engine("offline", runtime=BaselineRuntime())
    analyses = []
    for task in (
        engine.topics.classify(document),
        engine.sentiment.analyze(document),
        engine.entities.extract(document),
        engine.events.extract(document, ()),
    ):
        with suppress(NoPredictions):
            analyses.append(await task)
    content = {
        record.id: canonical(record.model_dump(mode="json")),
        record.id + ":analysis": canonical([a.model_dump(mode="json") for a in analyses]),
    }
    crypto = StandardCryptoProvider(keys)
    lineage = tuple(
        ProvenanceRecord(
            provenance_id=new_id("prov"),
            subject_id=subject,
            input_ids=() if index == 0 else (record.id,),
            operation="raw" if index == 0 else "public_headline_analysis",
            recorded_at=datetime.now(UTC),
            content_hash=crypto.hash(value),
        )
        for index, (subject, value) in enumerate(content.items())
    )
    return PublicRecord(
        metadata=record,
        analyses=tuple(analyses),
        provenance=ProvenanceService(crypto).sign(lineage, key_id="showcase"),
    )


async def export_collection(collection: Path, output: Path, key_dir: Path) -> PublicExport:
    rows = [Metadata.model_validate(r) for r in json.loads(collection.read_bytes())]
    if not (key_dir / "showcase.ed25519.key").exists():
        generate_development_keys(key_dir, "showcase")
    keys = FileKeyProvider(key_dir)
    records = [await process(r, keys) for r in rows]
    public_key = keys.verification_key("showcase").public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    export = PublicExport(
        exported_at=datetime.now(UTC),
        source_commit=commit,
        public_key=base64.b64encode(public_key).decode(),
        records=tuple(sorted(records, key=lambda r: r.metadata.id)),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(export.model_dump(mode="json")) + b"\n")
    return export
