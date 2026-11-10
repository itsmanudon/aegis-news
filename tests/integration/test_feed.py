"""Incremental feed against PostgreSQL: order, resume, re-signing and what is never sent."""
# ruff: noqa: F811 -- pytest imports the disposable-schema fixture by name.

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from aegis.intelligence.pipeline import stable_id
from aegis.persistence.models import (
    AnalysisRow,
    AssetMappingRow,
    Base,
    DocumentRow,
    EntityRow,
    IngestionRow,
    NewsEventRow,
    RawObjectRow,
    SourceRow,
)
from aegis.security.persistence import SignedManifestRow
from aegis.settings import Settings
from apps.api.main import create_app
from tests.ingestion.test_pipeline import repository  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.database]
FEED = "/api/v1/feed/documents"
BODY = "ARTICLE-BODY-MUST-NOT-LEAVE"
EVIDENCE = "EVIDENCE-SENTENCE-MUST-NOT-LEAVE"


def at(day, hour=0):
    return datetime(2026, 1, day, hour, tzinfo=UTC)


def identity(prefix, number):
    return f"{prefix}_{UUID(int=number)}"


def seed_doc(session, number, created, signed=None, last_signed=None):
    raw_id, ingestion_id = identity("raw", number), identity("ing", number)
    session.add(
        RawObjectRow(
            raw_object_id=raw_id,
            bucket="test",
            key=str(number),
            sha256="0" * 64,
            size_bytes=0,
            content_type="text/plain",
            created_at=created,
        )
    )
    session.flush()
    session.add(
        IngestionRow(
            ingestion_id=ingestion_id,
            source_id=identity("src", 1),
            raw_object_id=raw_id,
            source_url=f"https://example.test/story/{number}",
            first_seen_at=created,
            ingested_at=created,
            idempotency_key=str(number),
        )
    )
    session.flush()
    session.add(
        DocumentRow(
            document_id=identity("doc", number),
            ingestion_id=ingestion_id,
            source_id=identity("src", 1),
            title=f"Original Synthetic Story {number}",
            text=f"{BODY} {number}",
            language="en",
            published_at=created,
            first_seen_at=created,
            ingested_at=created,
            created_at=created,
            available_at=signed,
            last_signed_at=last_signed or signed,
        )
    )
    session.flush()
    if signed:
        manifest(session, number, signed)


def manifest(session, number, signed, salt=0):
    session.add(
        SignedManifestRow(
            manifest_hash=f"{number * 1000 + salt:064x}",
            created_at=signed,
            key_id="local",
            manifest={
                "records": [
                    {"subject_id": identity("raw", number), "operation": "raw"},
                    {"subject_id": identity("doc", number), "operation": "normalization"},
                ]
            },
        )
    )


def analysis(session, number, doc, kind, when, outputs):
    session.add(
        AnalysisRow(
            analysis_id=identity("ana", number),
            document_id=identity("doc", doc),
            analysis_type=kind,
            provider="synthetic",
            model_name=kind + "-fixture",
            model_version="1",
            configuration_hash="0" * 64,
            created_at=when,
            available_at=when,
            outputs=outputs,
        )
    )
    session.flush()


@pytest.fixture
def corpus(repository):
    with repository.sessions.begin() as session:
        session.add(
            SourceRow(
                source_id=identity("src", 1),
                name="Original Synthetic Publisher",
                kind="feed",
                url="https://example.test/",
                created_at=at(1),
            )
        )
        session.flush()
        seed_doc(session, 1, at(2), at(10))
        # Two documents signed in the same instant: the identifier breaks the tie.
        seed_doc(session, 3, at(4), at(11))
        seed_doc(session, 2, at(3), at(11))
        seed_doc(session, 4, at(5))  # never signed
        seed_doc(session, 5, at(6), at(12))

        for number, name in ((1, "Atlas Labs"), (2, "Unmapped Holdings")):
            session.add(
                EntityRow(
                    entity_id=identity("ent", number),
                    canonical_name=name,
                    kind="organization",
                    created_at=at(1),
                )
            )
        session.flush()
        session.add(
            AssetMappingRow(
                mapping_id=identity("map", 1),
                entity_id=identity("ent", 1),
                scheme="exchange_symbol",
                identifier="ATLS",
                venue="XNAS",
                created_at=at(1),
            )
        )
        analysis(
            session,
            1,
            1,
            "topic",
            at(9),
            [{"result_type": "topic", "label": "tech", "confidence": 0.7}],
        )
        analysis(
            session,
            2,
            1,
            "sentiment",
            at(9, 1),
            [{"result_type": "sentiment", "label": "positive", "score": 0.6, "confidence": 0.8}],
        )
        analysis(
            session,
            3,
            1,
            "embedding",
            at(9, 2),
            [{"result_type": "embedding", "values": [0.1, 0.2]}],
        )
        analysis(
            session,
            4,
            1,
            "entity_extraction",
            at(9, 3),
            [
                {
                    "result_type": "entity_extraction",
                    "surface": EVIDENCE,
                    "start_offset": 0,
                    "end_offset": 5,
                    "confidence": 0.9,
                }
            ],
        )
        analysis(
            session,
            5,
            1,
            "entity_resolution",
            at(9, 4),
            [
                {
                    "result_type": "entity_resolution",
                    "mention_id": identity("mention", n),
                    "entity_id": identity("ent", entity) if entity else None,
                    "confidence": confidence,
                }
                for n, entity, confidence in ((1, 1, 0.4), (2, 1, 0.9), (3, 2, 0.8), (4, None, 0.2))
            ],
        )
        analysis(
            session,
            6,
            1,
            "event_extraction",
            at(9, 5),
            [
                {
                    "result_type": "event_extraction",
                    "proposed_event_type": "product_launch",
                    "confidence": 0.75,
                    "document_id": identity("doc", 1),
                    "evidence_text": EVIDENCE,
                }
            ],
        )
        event_id = stable_id("evt", f"{identity('ana', 6)}:0")
        session.add(
            NewsEventRow(
                event_id=event_id,
                revision=1,
                summary=EVIDENCE,
                created_at=at(9, 5),
                available_at=at(9, 5),
                evidence_kind="model_output",
                analysis_id=identity("ana", 6),
            )
        )
        session.flush()
        session.execute(
            Base.metadata.tables["event_documents"]
            .insert()
            .values(event_id=event_id, revision=1, document_id=identity("doc", 1))
        )
    app = create_app(Settings(_env_file=None, security_enabled=False, otel_enabled=False))
    app.state.ingestion_service = SimpleNamespace(repository=repository)
    return TestClient(app), repository


def ids(payload):
    return [item["document"]["document_id"] for item in payload["data"]]


def docs(*numbers):
    return [identity("doc", number) for number in numbers]


def test_feed_is_ordered_by_signing_and_carries_no_article_text(corpus):
    client, _ = corpus
    before = datetime.now(UTC)
    response = client.get(FEED)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert ids(payload) == docs(1, 2, 3, 5)  # unsigned 4 is absent; 2 and 3 tie on time
    assert BODY not in response.text and EVIDENCE not in response.text
    assert payload["pagination"] == {"has_more": False, "next_cursor": None}
    assert payload["resume_cursor"]
    as_of = datetime.fromisoformat(payload["as_of"])
    assert before - timedelta(seconds=61) <= as_of <= datetime.now(UTC) - timedelta(seconds=60)

    first = payload["data"][0]
    assert set(first) == {"document", "source", "analyses", "instruments", "events", "manifests"}
    document = first["document"]
    assert "text" not in document
    assert document["url"] == "https://example.test/story/1"
    assert document["available_at"] == document["last_signed_at"] == "2026-01-10T00:00:00Z"
    assert first["source"]["name"] == "Original Synthetic Publisher"
    # Embeddings and the two extraction analyses are withheld; order is availability.
    assert [a["analysis_type"] for a in first["analyses"]] == [
        "topic",
        "sentiment",
        "entity_resolution",
    ]
    sentiment = first["analyses"][1]
    assert (sentiment["model_name"], sentiment["model_version"]) == ("sentiment-fixture", "1")
    assert sentiment["outputs"][0]["score"] == 0.6
    # One instrument: the mapped entity, at its best resolution confidence. The second
    # entity resolves but has no mapping, so it is not an instrument.
    assert first["instruments"] == [
        {
            "entity_id": identity("ent", 1),
            "canonical_name": "Atlas Labs",
            "kind": "organization",
            "mapping_id": identity("map", 1),
            "scheme": "exchange_symbol",
            "identifier": "ATLS",
            "venue": "XNAS",
            "resolution_analysis_id": identity("ana", 5),
            "confidence": 0.9,
        }
    ]
    (event,) = first["events"]
    assert "summary" not in event
    assert (event["event_type"], event["confidence"]) == ("product_launch", 0.75)
    assert event["analysis_id"] == identity("ana", 6)
    assert first["manifests"] == [
        {"manifest_hash": f"{1000:064x}", "key_id": "local", "signed_at": "2026-01-10T00:00:00Z"}
    ]
    assert payload["data"][1]["analyses"] == [] and payload["data"][1]["instruments"] == []


def test_feed_pages_resumes_and_picks_up_newly_signed_documents(corpus):
    client, repository = corpus
    first = client.get(FEED, params={"limit": 2}).json()
    assert ids(first) == docs(1, 2)
    assert first["pagination"]["has_more"]
    assert first["pagination"]["next_cursor"] == first["resume_cursor"]
    second = client.get(FEED, params={"limit": 2, "cursor": first["resume_cursor"]}).json()
    assert ids(second) == docs(3, 5) and not second["pagination"]["has_more"]
    # An empty page still says where to resume, and resuming is stable.
    empty = client.get(FEED, params={"cursor": second["resume_cursor"]}).json()
    assert empty["data"] == [] and empty["resume_cursor"] == second["resume_cursor"]
    with repository.sessions.begin() as session:
        session.execute(
            update(DocumentRow)
            .where(DocumentRow.document_id == identity("doc", 4))
            .values(available_at=at(13), last_signed_at=at(13))
        )
        manifest(session, 4, at(13))
    later = client.get(FEED, params={"cursor": empty["resume_cursor"]}).json()
    assert ids(later) == docs(4)
    assert client.get(FEED, params={"cursor": later["resume_cursor"]}).json()["data"] == []


def test_resigned_document_returns_once_more_with_its_new_analysis(corpus):
    client, repository = corpus
    done = client.get(FEED).json()["resume_cursor"]
    with repository.sessions.begin() as session:
        analysis(
            session,
            20,
            1,
            "sentiment",
            at(19),
            [{"result_type": "sentiment", "label": "negative", "score": -0.4, "confidence": 0.9}],
        )
        session.execute(
            update(DocumentRow)
            .where(DocumentRow.document_id == identity("doc", 1))
            .values(last_signed_at=at(20))
        )
        manifest(session, 1, at(20), salt=1)
    again = client.get(FEED, params={"cursor": done}).json()
    assert ids(again) == docs(1)
    item = again["data"][0]
    assert item["document"]["available_at"] == "2026-01-10T00:00:00Z"
    assert item["document"]["last_signed_at"] == "2026-01-20T00:00:00Z"
    assert [a["analysis_id"] for a in item["analyses"]][-1] == identity("ana", 20)
    assert [m["signed_at"] for m in item["manifests"]] == [
        "2026-01-10T00:00:00Z",
        "2026-01-20T00:00:00Z",
    ]
    # From the beginning the document now appears once, at its new position.
    assert ids(client.get(FEED).json()) == docs(2, 3, 5, 1)


def test_since_starts_inclusive_and_bad_arguments_are_rejected(corpus):
    client, _ = corpus
    assert ids(client.get(FEED, params={"since": at(11).isoformat()}).json()) == docs(2, 3, 5)
    assert client.get(FEED, params={"since": at(13).isoformat()}).json()["data"] == []
    cursor = client.get(FEED).json()["resume_cursor"]
    for params in (
        {"cursor": cursor, "since": at(11).isoformat()},
        {"cursor": "not-a-cursor"},
        {"cursor": cursor[:-2]},
        {"since": "2026-01-11T00:00:00"},  # no offset
        {"limit": 0},
        {"limit": 101},
    ):
        response = client.get(FEED, params=params)
        assert response.status_code == 422, params
        assert response.json()["error"]["code"] == "INVALID_ARGUMENT"


def test_rows_signed_inside_the_safety_lag_are_held_back(corpus):
    client, repository = corpus
    now = datetime.now(UTC)
    with repository.sessions.begin() as session:
        seed_doc(session, 9, now - timedelta(hours=1), now - timedelta(seconds=5))
    payload = client.get(FEED).json()
    assert identity("doc", 9) not in ids(payload)
    assert datetime.fromisoformat(payload["as_of"]) < now - timedelta(seconds=5)
    # The cursor stops before the held-back row, so the next sync still reaches it.
    assert ids(payload)[-1] == identity("doc", 5)
