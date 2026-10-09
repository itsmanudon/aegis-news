"""Real HTTP sprint probes and original synthetic media fixtures, isolated runtime only.

No provider requests, downloads, copied publisher content, or fabricated model outputs.
Image URL delivery is a separately disclosed browser fixture, not backend object delivery.
"""

import asyncio
import base64
import json
import urllib.error
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select

from aegis.ingestion.runtime import make_service
from aegis.persistence.models import AnalysisRow
from aegis.providers.models import ExternalNewsRecord, YouTubeReference
from aegis.providers.persistence import ProviderStore, YouTubeReferenceRow
from scripts.completion_integration import API, ROOT, RUNTIME, assert_owned_runtime
from scripts.demo_seed import DemoClient

DEMO_SOURCE = "DEMO Completion Newsroom — Original CC0 Synthetic"
DEMO_HOST = "https://completion.example.test"


def guard() -> None:
    assert_owned_runtime()


def observed_window(values: list[str]) -> dict[str, str]:
    timestamps = [datetime.fromisoformat(value).astimezone(UTC) for value in values]
    if not timestamps or any(datetime.fromisoformat(value).tzinfo is None for value in values):
        raise ValueError("An aware observed fixture timestamp is required")
    start = min(timestamps).replace(hour=0, minute=0, second=0, microsecond=0)
    end = max(timestamps).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    if end - start > timedelta(days=366):
        raise ValueError("Observed fixture window exceeds the supported bound")
    return {"start": start.isoformat(), "end": end.isoformat()}


def refresh_synthetic_reference(value: YouTubeReference, now: datetime) -> YouTubeReference:
    if value.expires_at > now:
        return value
    return value.model_copy(
        update={"last_refreshed_at": now, "expires_at": now + timedelta(days=29)}
    )


def denied(client: DemoClient, path: str, code: int, role: str | None = "analyst") -> None:
    try:
        client.request(path, role=role)
    except urllib.error.HTTPError as exc:
        assert exc.code == code, (path, exc.code, code)
    else:
        raise AssertionError("Request unexpectedly permitted: " + path)


def collection(client: DemoClient, path: str, params: dict[str, Any]) -> tuple[list[Any], str]:
    values: list[Any] = []
    cursor = None
    snapshot = ""
    for _ in range(100):
        query = {**params, **({"cursor": cursor} if cursor else {})}
        report = client.request(path + "?" + urlencode(query), role="analyst")
        assert len(report["data"]) <= params["limit"]
        if "as_of" in report:
            snapshot = snapshot or report["as_of"]
            assert snapshot == report["as_of"]
        values.extend(report["data"])
        if not report["pagination"]["has_more"]:
            return values, snapshot
        next_cursor = report["pagination"]["next_cursor"]
        assert next_cursor and next_cursor != cursor
        cursor = next_cursor
    raise AssertionError("Bounded fixture pagination exceeded 100 pages")


async def seed_media(client: DemoClient) -> dict[str, Any]:
    guard()
    sources, _ = collection(client, "/api/v1/sources", {"limit": 100})
    source = next((value for value in sources if value["name"] == DEMO_SOURCE), None)
    if source is None:
        source = client.request(
            "/api/v1/sources", {"name": DEMO_SOURCE, "kind": "upload", "url": DEMO_HOST}
        )["data"]
    service = make_service(client.settings)
    store = ProviderStore(service.repository.sessions)
    original_image = (ROOT / "data/samples/demo-image.png").read_bytes()
    published = datetime(2026, 10, 7, 10, tzinfo=UTC)
    fixtures = (
        ExternalNewsRecord(
            provider="gnews",
            provider_item_id="completion-cc0-technology-v1",
            publisher_name=DEMO_SOURCE,
            publisher_url=DEMO_HOST,
            article_url=DEMO_HOST + "/stories/technology-workshop",
            title="DEMO Atlas Labs opens a public technology workshop",
            description="Original CC0 synthetic demo. Atlas Labs launched new software and "
            "announced strong profit growth during a public technology workshop.",
            language="en",
            published_at=published,
            image_url=DEMO_HOST + "/images/original-cc0-demo.png",
            video_url=DEMO_HOST + "/videos/DEMO0000001",
        ),
        ExternalNewsRecord(
            provider="newsdata",
            provider_item_id="completion-cc0-community-v1",
            publisher_name=DEMO_SOURCE,
            publisher_url=DEMO_HOST,
            article_url=DEMO_HOST + "/stories/community-research",
            title="DEMO Cedar Health announces a community research programme",
            description="Original CC0 synthetic demo. Cedar Health announced a hospital "
            "research programme with improved patient care and strong community support.",
            language="en",
            published_at=published,
            image_url=DEMO_HOST + "/images/unavailable-demo.png",
        ),
        ExternalNewsRecord(
            provider="newsapi",
            provider_item_id="completion-cc0-unknown-date-v1",
            publisher_name=DEMO_SOURCE,
            publisher_url=DEMO_HOST,
            article_url=DEMO_HOST + "/stories/undated-notice",
            title="DEMO Undated French-language community notice",
            description="Démonstration synthétique originale CC0. Une réunion publique est "
            "annoncée dans une commune fictive. Langue française, date inconnue.",
            language="fr",
            published_at=None,
        ),
    )
    records: list[dict[str, Any]] = []
    try:
        for index, fixture in enumerate(fixtures):
            row, duplicate = store.prepare(fixture, source["source_id"])
            payload = dict(row.request)
            if index == 0:
                payload["media"] = [
                    {
                        "kind": "image",
                        "content_type": "image/png",
                        "content_base64": base64.b64encode(original_image).decode(),
                    }
                ]
            elif index == 1:
                payload["media"] = [
                    {
                        "kind": "attachment",
                        "content_type": "text/plain",
                        "content_base64": base64.b64encode(
                            b"Original CC0 synthetic programme attachment."
                        ).decode(),
                    }
                ]
            submission = client.request("/api/v1/ingestions", payload)["data"]
            store.submitted(row.article_id, submission["workflow_id"])
            result = await client.wait(submission["workflow_id"])
            store.completed(submission["workflow_id"], result["document_id"])
            assert client.request(
                f"/api/v1/documents/{result['document_id']}/verify", {}, "analyst"
            )["data"]["valid"]
            view = client.request(
                f"/api/v1/documents/{result['document_id']}/intelligence", role="analyst"
            )["data"]
            records.append(
                {
                    "article_id": row.article_id,
                    "document_id": result["document_id"],
                    "title": fixture.title,
                    "language": fixture.language,
                    "published_at": fixture.published_at.isoformat()
                    if fixture.published_at
                    else None,
                    "first_seen_at": view["document"]["first_seen_at"],
                    "image_url": fixture.image_url,
                    "duplicate_acquisition": duplicate,
                    "stored_assets": [
                        {
                            "media_id": value["media_id"],
                            "kind": value["kind"],
                            "content_type": value["object"]["content_type"],
                            "sha256": value["object"]["sha256"],
                        }
                        for value in view["media"]
                    ],
                    "workflow": result,
                }
            )
        refreshed = datetime.now(UTC)
        videos = [
            YouTubeReference(
                video_id=f"DEMO000000{index}",
                title=f"DEMO Original CC0 synthetic video metadata {index}",
                channel_id="completion-cc0-synthetic",
                channel_title=DEMO_SOURCE,
                published_at=published,
                thumbnail_url=DEMO_HOST + "/images/original-cc0-demo.png",
                youtube_url=DEMO_HOST + f"/videos/DEMO000000{index}",
                last_refreshed_at=refreshed,
                expires_at=refreshed + timedelta(days=29),
            )
            for index in (1, 2)
        ]
        with service.repository.sessions() as session:
            for index, video in enumerate(videos):
                stored = session.get(YouTubeReferenceRow, video.video_id)
                if stored:
                    videos[index] = refresh_synthetic_reference(
                        YouTubeReference.model_validate(stored.metadata_value),
                        refreshed,
                    )
        store.videos(videos)
        return {
            "source_id": source["source_id"],
            "source_name": DEMO_SOURCE,
            "articles": records,
            "video_ids": [value.video_id for value in videos],
            "video_timestamps": [
                {
                    "video_id": value.video_id,
                    "last_refreshed_at": value.last_refreshed_at.isoformat(),
                    "expires_at": value.expires_at.isoformat(),
                }
                for value in videos
            ],
            "analytics_windows": {
                "published_at": observed_window(
                    [value["published_at"] for value in records if value["published_at"]]
                ),
                "first_seen_at": observed_window([value["first_seen_at"] for value in records]),
            },
            "demo_image_url": DEMO_HOST + "/images/original-cc0-demo.png",
            "original_image_path": str(ROOT / "data/samples/demo-image.png"),
            "image_delivery": "Remote demo URLs require separately disclosed browser interception; "
            "stored image bytes are real MinIO assets. No external video inference or playback.",
            "provider_calls": 0,
        }
    finally:
        service.repository.close()


def counts(report: dict[str, Any], documents: list[Any]) -> None:
    assert report["population_count"] == len(documents)
    assert report["classified_count"] + report["no_assessment_count"] == len(documents)
    assert sum(value["document_count"] for value in report["coverage"]) == len(documents)
    assert (
        sum(value["classified_count"] for value in report["coverage"]) == report["classified_count"]
    )
    assert sum(value["document_count"] for value in report["sources"]) + report[
        "sources_other_count"
    ] == len(documents)
    assert (
        sum(value["document_count"] for value in report["sentiment"]) == report["classified_count"]
    )
    assert (
        sum(value["document_count"] for value in report["models"]) + report["models_other_count"]
        == report["classified_count"]
    )


async def probe() -> dict[str, Any]:
    guard()
    client = DemoClient(API)
    media = await seed_media(client)
    checks: list[str] = []
    window = media["analytics_windows"]["first_seen_at"]
    protected = (
        "/topics",
        "/topics/invalid",
        "/topics/invalid/documents",
        "/discovery",
        "/analytics?" + urlencode(window),
        "/provider-articles",
        "/youtube-references",
    )
    for path in protected:
        denied(client, "/api/v1" + path, 401, None)
        denied(client, "/api/v1" + path, 403, "source_manager")
    checks.append("anonymous_401_and_missing_document_read_scope_403")
    assert client.request("/api/v1/topics", role="viewer")["data"]
    assert client.request("/api/v1/discovery", role="analyst")["data"]
    assert all(
        not value["enabled"]
        for value in client.request("/api/v1/providers")["data"]
        if value["provider"] != "gdelt"
    )
    checks.append("viewer_and_analyst_reads_allowed_without_provider_acquisition")

    topics, cutoff = collection(client, "/api/v1/topics", {"limit": 2})
    assert len({value["topic_id"] for value in topics}) == len(topics)
    selections = []
    for topic in topics:
        detail = client.request(
            "/api/v1/topics/" + topic["topic_id"] + "?" + urlencode({"as_of": cutoff}),
            role="analyst",
        )["data"]
        members, _ = collection(
            client,
            "/api/v1/topics/" + topic["topic_id"] + "/documents",
            {"limit": 1, "as_of": cutoff},
        )
        assert detail == topic
        assert (
            len({value["document"]["document_id"] for value in members}) == topic["document_count"]
        )
        for member in members:
            assert member["source"]["source_id"] == member["document"]["source_id"]
            assert member["model"] == topic["model"]
            assert 0 <= member["confidence"] <= 1
            view = client.request(
                "/api/v1/documents/"
                + member["document"]["document_id"]
                + "/intelligence?"
                + urlencode({"as_of": cutoff}),
                role="analyst",
            )["data"]
            analysis = next(
                value for value in view["analyses"] if value["analysis_id"] == member["analysis_id"]
            )
            assert analysis["analysis_type"] == "topic"
            assert any(value.get("label") == topic["label"] for value in analysis["outputs"])
        selections.append(
            {
                "topic_id": topic["topic_id"],
                "label": topic["label"],
                "document_count": topic["document_count"],
                "document_ids": [value["document"]["document_id"] for value in members],
            }
        )
    checks.append("topic_directory_detail_membership_model_and_source_evidence")

    discovery, snapshot = collection(client, "/api/v1/discovery", {"limit": 3})
    identifiers = [value["document"]["document_id"] for value in discovery]
    assert len(set(identifiers)) == len(identifiers)

    def key(value: Any) -> tuple[bool, float, str]:
        date = value["document"]["published_at"]
        return (
            date is None,
            -datetime.fromisoformat(date).timestamp() if date else 0,
            value["document"]["document_id"],
        )

    assert discovery == sorted(discovery, key=key)
    first = client.request("/api/v1/discovery?limit=1", role="analyst")
    cursor = first["pagination"]["next_cursor"]
    assert cursor
    denied(
        client,
        "/api/v1/discovery?" + urlencode({"limit": 1, "cursor": cursor, "q": "changed"}),
        422,
    )
    denied(
        client,
        "/api/v1/discovery?" + urlencode({"limit": 1, "cursor": cursor, "order": "first_seen_at"}),
        422,
    )
    for path in (
        "/discovery?limit=101",
        "/discovery?cursor=invalid",
        "/topics?limit=0",
        "/topics/invalid",
    ):
        denied(client, "/api/v1" + path, 422)
    checks.append("global_chronological_pages_nulls_ties_unique_and_cursor_filter_binding")

    reports = {}
    for basis in ("published_at", "first_seen_at"):
        params = {
            **media["analytics_windows"][basis],
            "source_id": media["source_id"],
            "time_basis": basis,
            "as_of": snapshot,
        }
        report = client.request("/api/v1/analytics?" + urlencode(params), role="analyst")["data"]
        supporting, _ = collection(client, "/api/v1/discovery", {**params, "limit": 1})
        counts(report, supporting)
        reports[basis] = report
    assert reports["published_at"]["population_count"] == 2
    assert reports["published_at"]["unknown_time_count"] == 1
    assert reports["first_seen_at"]["population_count"] == 3
    assert reports["first_seen_at"]["classified_count"] == 2
    assert reports["first_seen_at"]["no_assessment_count"] == 1
    unsupported = media["articles"][2]["document_id"]
    service = make_service(client.settings)
    try:
        with service.repository.sessions() as session:
            assert not list(
                session.scalars(select(AnalysisRow).where(AnalysisRow.document_id == unsupported))
            )
    finally:
        service.repository.close()
    checks.append("real_aggregate_denominators_and_unknown_unassessed_outcomes")
    topic_analytics = []
    for selection in selections:
        params = {
            **window,
            "topic_id": selection["topic_id"],
            "time_basis": "first_seen_at",
            "as_of": cutoff,
        }
        report = client.request("/api/v1/analytics?" + urlencode(params), role="analyst")["data"]
        supporting, _ = collection(client, "/api/v1/discovery", {**params, "limit": 1})
        counts(report, supporting)
        assert {value["document"]["document_id"] for value in supporting} <= set(
            selection["document_ids"]
        )
        topic_analytics.append(
            {
                "topic_id": selection["topic_id"],
                "population_count": report["population_count"],
                "classified_count": report["classified_count"],
            }
        )
    checks.append("topic_filtered_analytics_drilldown_population_equality")
    for params in (
        {},
        {"start": window["start"].split("T")[0], "end": window["end"].split("T")[0]},
        {"start": window["end"], "end": window["start"]},
        {
            "start": (datetime.fromisoformat(window["end"]) - timedelta(days=367)).isoformat(),
            "end": window["end"],
        },
    ):
        denied(client, "/api/v1/analytics?" + urlencode(params), 422)
    earliest = min(datetime.fromisoformat(value["document"]["created_at"]) for value in discovery)
    historical = urlencode({"as_of": (earliest - timedelta(seconds=1)).isoformat()})
    assert not client.request("/api/v1/discovery?" + historical, role="analyst")["data"]
    assert not client.request("/api/v1/topics?" + historical, role="analyst")["data"]
    checks.append("aware_bounded_windows_and_actual_persistence_availability_cutoffs")
    articles, _ = collection(client, "/api/v1/provider-articles", {"limit": 1})
    videos, _ = collection(client, "/api/v1/youtube-references", {"limit": 1})
    assert {value["article_id"] for value in media["articles"]} <= {
        value["article_id"] for value in articles
    }
    assert set(media["video_ids"]) <= {value["video_id"] for value in videos}
    for article in media["articles"]:
        evidence = client.request(
            f"/api/v1/documents/{article['document_id']}/acquisition", role="analyst"
        )["data"]
        assert evidence and evidence[0]["publisher_name"] == DEMO_SOURCE
    assert all(datetime.fromisoformat(value["expires_at"]) > datetime.now(UTC) for value in videos)
    checks.append("stored_media_acquisition_attribution_video_expiry_and_bounded_pages")
    return {
        "result": "passed",
        "checks": checks,
        "media": media,
        "topic_selections": selections,
        "analytics": reports,
        "topic_analytics": topic_analytics,
        "discovery_document_count": len(discovery),
        "as_of": snapshot,
        "limitations": [
            "Remote demo images require disclosed browser interception.",
            "No external video inference/playback or provider acquisition occurred.",
            "Past edits to mutable source/document metadata cannot be reconstructed.",
        ],
    }


def main() -> None:
    report = asyncio.run(probe())
    destination = RUNTIME / "product-probe.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks": report["checks"],
                "report": str(destination),
                "source_id": report["media"]["source_id"],
                "articles": report["media"]["articles"],
                "video_ids": report["media"]["video_ids"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
