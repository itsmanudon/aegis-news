"""Incremental feed against PostgreSQL: order, resume, re-signing and what is never sent."""
# ruff: noqa: F811 -- pytest imports the disposable-schema fixture by name.

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
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
    current_xid,
)
from aegis.security.auth import TokenValidator
from aegis.security.persistence import SignedManifestRow
from aegis.security.service_token import mint_service_token
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


def seed_doc(session, number, created, signed=None, last_signed=None, analyses=()):
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
            # As AnalysisPipeline.sign does: the signing transaction's id.
            signed_xid=current_xid() if (last_signed or signed) else None,
        )
    )
    session.flush()
    if signed:
        manifest(session, number, signed, analyses=analyses)


def manifest(session, number, signed, salt=0, analyses=()):
    """A signed run of document ``number`` that signed the analyses numbered ``analyses``."""
    session.add(
        SignedManifestRow(
            manifest_hash=f"{number * 1000 + salt:064x}",
            created_at=signed,
            key_id="local",
            manifest={
                "records": [
                    {"subject_id": identity("raw", number), "operation": "raw"},
                    {"subject_id": identity("doc", number), "operation": "normalization"},
                    *(
                        {"subject_id": identity("ana", n), "operation": "analysis"}
                        for n in analyses
                    ),
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
        seed_doc(session, 1, at(2), at(10), analyses=range(1, 7))
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
        # Analysed after the run was signed, so no bundle may show it yet.
        analysis(
            session,
            7,
            1,
            "topic",
            at(9, 6),
            [{"result_type": "topic", "label": "unsigned", "confidence": 0.9}],
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
    assert before <= as_of <= datetime.now(UTC)

    first = payload["data"][0]
    assert set(first) == {
        "document",
        "source",
        "analyses",
        "entities",
        "instruments",
        "events",
        "manifests",
        "withdrawal",
    }
    assert first["withdrawal"] is None
    # Every resolved entity, mapped or not, so the consumer can join mappings added later.
    assert [(e["entity_id"], e["confidence"]) for e in first["entities"]] == [
        (identity("ent", 1), 0.9),
        (identity("ent", 2), 0.8),
    ]
    document = first["document"]
    assert "text" not in document
    assert document["url"] == "https://example.test/story/1"
    assert document["available_at"] == document["last_signed_at"] == "2026-01-10T00:00:00Z"
    assert first["source"]["name"] == "Original Synthetic Publisher"
    # Embeddings and the two extraction analyses are withheld, and so is analysis 7, which
    # no run has signed. Order is availability.
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
            .values(available_at=at(13), last_signed_at=at(13), signed_xid=current_xid())
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
            .values(last_signed_at=at(20), signed_xid=current_xid())
        )
        # The second run signs the topic, the resolution and the new sentiment only.
        manifest(session, 1, at(20), salt=1, analyses=(1, 5, 20))
    again = client.get(FEED, params={"cursor": done}).json()
    assert ids(again) == docs(1)
    item = again["data"][0]
    assert item["document"]["available_at"] == "2026-01-10T00:00:00Z"
    assert item["document"]["last_signed_at"] == "2026-01-20T00:00:00Z"
    # The bundle is the latest run: the old sentiment and the event it did not sign are gone.
    assert [a["analysis_id"] for a in item["analyses"]] == [
        identity("ana", 1),
        identity("ana", 5),
        identity("ana", 20),
    ]
    assert item["events"] == []
    assert [i["mapping_id"] for i in item["instruments"]] == [identity("map", 1)]
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


def test_a_signing_transaction_still_open_holds_the_feed_back(corpus):
    """AG-8: a transaction that commits late is delayed, never skipped."""
    client, repository = corpus
    done = client.get(FEED).json()["resume_cursor"]
    with repository.sessions.begin() as session:
        seed_doc(session, 9, at(14))  # not signed yet

    def sign(session, number, when):
        session.execute(
            update(DocumentRow)
            .where(DocumentRow.document_id == identity("doc", number))
            .values(available_at=when, last_signed_at=when, signed_xid=current_xid())
        )

    slow = repository.sessions()
    try:
        sign(slow, 4, at(15))  # takes a transaction id, then stays open
        with repository.sessions.begin() as fast:
            sign(fast, 9, at(16))  # a later id, committed first
        held = client.get(FEED, params={"cursor": done}).json()
        # Document 9 is committed but waits for the older, open transaction.
        assert held["data"] == [] and held["resume_cursor"] == done
        slow.commit()
    finally:
        slow.close()
    released = client.get(FEED, params={"cursor": done}).json()
    assert ids(released) == docs(4, 9)


def test_instrument_filters_narrow_the_feed_and_bind_the_cursor(corpus):
    client, repository = corpus
    # Only document 1 resolves to a mapped entity (ATLS on XNAS).
    mapped = client.get(FEED, params={"mapped": True}).json()
    assert ids(mapped) == docs(1) and not mapped["pagination"]["has_more"]
    for params, expected in (
        ({"venue": "XNAS"}, docs(1)),
        ({"venue": "XNAS", "identifier": "ATLS", "scheme": "exchange_symbol"}, docs(1)),
        ({"venue": "XNYS"}, []),
        ({"identifier": "MSFT"}, []),
        ({"scheme": "isin"}, []),
    ):
        assert ids(client.get(FEED, params=params).json()) == expected, params
    assert client.get(FEED, params={"scheme": "ticker"}).status_code == 422
    # A cursor resumes only the stream it came from.
    unfiltered = client.get(FEED).json()["resume_cursor"]
    assert client.get(FEED, params={"cursor": unfiltered, "mapped": True}).status_code == 422
    assert client.get(FEED, params={"cursor": mapped["resume_cursor"]}).status_code == 422
    resumed = client.get(FEED, params={"cursor": mapped["resume_cursor"], "mapped": True})
    assert resumed.status_code == 200 and resumed.json()["data"] == []
    # A mapping added later links documents from then on, and a re-signed one resurfaces.
    with repository.sessions.begin() as session:
        session.add(
            AssetMappingRow(
                mapping_id=identity("map", 2),
                entity_id=identity("ent", 2),
                scheme="exchange_symbol",
                identifier="UNMP",
                venue="XNYS",
                created_at=at(15),
            )
        )
    assert ids(client.get(FEED, params={"venue": "XNYS"}).json()) == docs(1)
    both = client.get(FEED, params={"mapped": True}).json()["data"][0]["instruments"]
    assert [(i["identifier"], i["venue"]) for i in both] == [("ATLS", "XNAS"), ("UNMP", "XNYS")]


def test_a_feed_only_service_token_reads_the_feed_and_nothing_else(corpus):
    _, repository = corpus
    key = Ed25519PrivateKey.generate()
    settings = Settings(
        _env_file=None,
        security_enabled=True,
        oidc_issuer="https://owner.test/aegis",
        oidc_audience="aegisnews",
        oidc_algorithms=["EdDSA"],
        otel_enabled=False,
    )
    app = create_app(settings)
    app.state.ingestion_service = SimpleNamespace(repository=repository)
    app.state.token_validator = TokenValidator(settings, public_keys={"sync": key.public_key()})

    def bearer(*scopes):
        token = mint_service_token(
            key,
            key_id="sync",
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            client_id="stockviz-sync",
            scopes=scopes,
            lifetime=timedelta(minutes=5),
            maximum_lifetime=timedelta(seconds=settings.oidc_max_token_lifetime),
        )
        return {"Authorization": "Bearer " + token}

    with TestClient(app) as client:
        assert client.get(FEED).status_code == 401
        feed = client.get(FEED, headers=bearer("feed:read"))
        assert feed.status_code == 200, feed.text
        assert ids(feed.json()) == docs(1, 2, 3, 5)
        listings = client.get("/api/v1/assets/mappings", headers=bearer("feed:read"))
        assert listings.status_code == 200, listings.text
        assert [m["identifier"] for m in listings.json()["data"]] == ["ATLS"]
        # The same token opens no route that returns article text or accepts a write.
        for method, path in (
            ("GET", "/api/v1/documents"),
            ("GET", "/api/v1/documents/" + identity("doc", 1)),
            ("GET", "/api/v1/events"),
            ("GET", "/api/v1/sources"),
            ("POST", "/api/v1/sources"),
        ):
            denied = client.request(method, path, headers=bearer("feed:read"))
            assert denied.status_code == 403, (method, path, denied.status_code)
        # The document scopes do not open the feed.
        wide = bearer("documents:read", "events:read")
        assert client.get(FEED, headers=wide).status_code == 403
        assert client.get("/api/v1/assets/mappings", headers=wide).status_code == 403


def test_a_withdrawn_document_returns_once_as_a_tombstone(corpus):
    """AG-11: the consumer is told to delete it; nothing is removed from Aegis."""
    from aegis.jobs.withdraw import withdraw

    client, repository = corpus
    done = client.get(FEED).json()["resume_cursor"]
    assert withdraw(repository.sessions, identity("doc", 1), "  publisher takedown ") == "withdrawn"
    assert withdraw(repository.sessions, identity("doc", 1), "again") == "already_withdrawn"
    assert withdraw(repository.sessions, identity("doc", 4), "x") == "not_signed"
    assert withdraw(repository.sessions, identity("doc", 99), "x") == "not_found"
    with pytest.raises(ValueError):
        withdraw(repository.sessions, identity("doc", 2), " ")
    later = client.get(FEED, params={"cursor": done}).json()
    (item,) = later["data"]
    assert item["document"]["document_id"] == identity("doc", 1)
    assert item["withdrawal"]["reason"] == "publisher takedown"
    assert item["analyses"] == item["entities"] == item["instruments"] == item["events"] == []
    assert item["manifests"]  # the signatures are kept
    # Withdrawing again did not move it: the next sync is empty.
    assert client.get(FEED, params={"cursor": later["resume_cursor"]}).json()["data"] == []
