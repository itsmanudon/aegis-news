"""Actual PostgreSQL projections: historical membership, ordering and aggregate denominators."""
# ruff: noqa: F811 -- pytest imports the disposable-schema fixture by name.

import json
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from aegis.persistence.models import AnalysisRow, DocumentRow, IngestionRow, RawObjectRow, SourceRow
from aegis.settings import Settings
from apps.api.main import create_app
from tests.ingestion.test_pipeline import repository  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.database]


def at(day):
    return datetime(2026, 1, day, tzinfo=UTC)


def identity(prefix, number):
    return f"{prefix}_{UUID(int=number)}"


def seed_doc(session, number, published, created):
    source_id = identity("src", 1)
    raw_id, ingestion_id = identity("raw", number), identity("ing", number)
    session.add(
        RawObjectRow(
            raw_object_id=raw_id,
            bucket="test",
            key=str(number),
            sha256="0" * 64,
            size_bytes=0,
            content_type="text/plain",
            created_at=at(created),
        )
    )
    session.flush()
    session.add(
        IngestionRow(
            ingestion_id=ingestion_id,
            source_id=source_id,
            raw_object_id=raw_id,
            first_seen_at=at(created),
            ingested_at=at(created),
            idempotency_key=str(number),
        )
    )
    session.flush()
    session.add(
        DocumentRow(
            document_id=identity("doc", number),
            ingestion_id=ingestion_id,
            source_id=source_id,
            title=f"Original Synthetic Story {number}",
            text="Synthetic reporting",
            published_at=at(published) if published else None,
            first_seen_at=at(created),
            ingested_at=at(created),
            created_at=at(created),
        )
    )
    session.flush()


def assessment(session, number, doc, kind, day, outputs, version="1"):
    session.add(
        AnalysisRow(
            analysis_id=identity("ana", number),
            document_id=identity("doc", doc),
            analysis_type=kind,
            provider="synthetic",
            model_name=kind + "-fixture",
            model_version=version,
            configuration_hash="0" * 64,
            created_at=at(day),
            available_at=at(day),
            outputs=outputs,
        )
    )


def topic(label="technology", confidence=0.7):
    return {"result_type": "topic", "label": label, "confidence": confidence}


def sentiment(label, entity=None):
    return {
        "result_type": "sentiment",
        "label": label,
        "score": 0,
        "confidence": 0.8,
        "entity_id": entity,
    }


@pytest.fixture
def corpus(repository):
    with repository.sessions.begin() as session:
        session.add(
            SourceRow(
                source_id=identity("src", 1),
                name="Original Synthetic Publisher",
                kind="upload",
                created_at=at(1),
            )
        )
        session.flush()
        for number, published, created in (
            (1, 3, 4),
            (2, 3, 5),
            (3, None, 6),
            (4, 10, 11),
            (5, 1, 20),
            (6, 2, 4),
        ):
            seed_doc(session, number, published, created)
        assessment(session, 1, 1, "topic", 5, [topic()])
        assessment(session, 2, 1, "topic", 20, [topic("business")])
        assessment(session, 3, 2, "topic", 7, [topic(confidence=0.8), topic(confidence=0.9)])
        assessment(session, 4, 3, "topic", 8, [topic()], version="2")
        assessment(session, 5, 4, "topic", 12, [topic("business")])
        assessment(session, 11, 1, "sentiment", 6, [sentiment("positive")])
        assessment(session, 12, 1, "sentiment", 20, [sentiment("negative")])
        assessment(session, 13, 1, "sentiment", 10, [sentiment("negative", identity("ent", 1))])
        assessment(session, 14, 2, "sentiment", 8, [sentiment("mixed")])
        assessment(session, 15, 4, "sentiment", 12, [sentiment("neutral")])
    app = create_app(Settings(_env_file=None, security_enabled=False, otel_enabled=False))
    from types import SimpleNamespace

    app.state.ingestion_service = SimpleNamespace(repository=repository)
    return TestClient(app), repository


def test_topics_select_before_cutoff_and_deduplicate_matching_outputs(corpus):
    client, _ = corpus
    response = client.get("/api/v1/topics", params={"as_of": at(15).isoformat(), "limit": 2})
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["pagination"]["has_more"]
    second = client.get(
        "/api/v1/topics", params={"cursor": first["pagination"]["next_cursor"], "limit": 2}
    ).json()
    topics = first["data"] + second["data"]
    tech = next(
        value
        for value in topics
        if value["label"] == "technology" and value["model"]["model_version"] == "1"
    )
    assert tech["document_count"] == 2
    assert (
        next(value for value in topics if value["model"]["model_version"] == "2")["document_count"]
        == 1
    )
    topic_id = tech["topic_id"]
    detail = client.get(f"/api/v1/topics/{topic_id}", params={"as_of": at(15).isoformat()}).json()[
        "data"
    ]
    assert detail == tech
    members = client.get(
        f"/api/v1/topics/{topic_id}/documents", params={"as_of": at(15).isoformat()}
    ).json()["data"]
    assert [value["document"]["document_id"] for value in members] == [
        identity("doc", 1),
        identity("doc", 2),
    ]
    assert members[1]["confidence"] == 0.9 and members[0]["analysis_id"] == identity("ana", 1)
    assert members[0]["source"]["name"] == "Original Synthetic Publisher"
    latest = client.get(f"/api/v1/topics/{topic_id}", params={"as_of": at(25).isoformat()}).json()[
        "data"
    ]
    assert latest["document_count"] == 1


def test_discovery_orders_globally_and_freezes_snapshot_between_pages(corpus):
    client, repository = corpus
    params = {"as_of": at(15).isoformat(), "limit": 2}
    first = client.get("/api/v1/discovery", params=params)
    assert first.status_code == 200, first.text
    page = first.json()
    assert [value["document"]["document_id"] for value in page["data"]] == [
        identity("doc", 4),
        identity("doc", 1),
    ]
    with repository.sessions.begin() as session:
        seed_doc(session, 7, 2, 16)
    seen = page["data"]
    while page["pagination"]["has_more"]:
        page = client.get(
            "/api/v1/discovery", params={"limit": 2, "cursor": page["pagination"]["next_cursor"]}
        ).json()
        seen += page["data"]
    assert [value["document"]["document_id"] for value in seen] == [
        identity("doc", i) for i in (4, 1, 2, 6, 3)
    ]
    assert seen[-1]["document"]["published_at"] is None
    replay = client.get(
        "/api/v1/discovery",
        params={"cursor": first.json()["pagination"]["next_cursor"], "q": "other"},
    )
    assert replay.status_code == 422


def test_analytics_unique_population_document_sentiment_and_exact_drilldown(corpus):
    client, _ = corpus
    params = {"start": at(1).isoformat(), "end": at(15).isoformat(), "as_of": at(15).isoformat()}
    response = client.get("/api/v1/analytics", params=params)
    assert response.status_code == 200, response.text
    report = response.json()["data"]
    assert (
        report["population_count"],
        report["classified_count"],
        report["no_assessment_count"],
        report["unknown_time_count"],
    ) == (4, 3, 1, 1)
    assert {value["label"]: value["document_count"] for value in report["sentiment"]} == {
        "positive": 1,
        "neutral": 1,
        "negative": 0,
        "mixed": 1,
    }
    assert (
        sum(value["document_count"] for value in report["coverage"]) == report["population_count"]
    )
    assert [value["day"] for value in report["coverage"]] == [
        "2026-01-02",
        "2026-01-03",
        "2026-01-10",
    ]
    assert report["sources"][0]["document_count"] == 4
    discovery = client.get(
        "/api/v1/discovery", params={**params, "time_basis": "published_at"}
    ).json()["data"]
    assert len(discovery) == report["population_count"]
    topics = client.get("/api/v1/topics", params={"as_of": at(15).isoformat()}).json()["data"]
    exact = next(
        value["topic_id"]
        for value in topics
        if value["label"] == "technology" and value["model"]["model_version"] == "1"
    )
    params["topic_id"] = exact
    scoped = client.get("/api/v1/analytics", params=params).json()["data"]
    assert (scoped["population_count"], scoped["classified_count"]) == (2, 2)
    assert len(client.get("/api/v1/discovery", params=params).json()["data"]) == 2
    empty = client.get(
        "/api/v1/analytics",
        params={
            "start": at(13).isoformat(),
            "end": at(14).isoformat(),
            "as_of": at(15).isoformat(),
        },
    ).json()["data"]
    assert empty["population_count"] == 0 and empty["coverage"] == []


def test_topic_identity_keeps_case_and_configuration_separate(corpus):
    client, repository = corpus
    with repository.sessions.begin() as session:
        assessment(session, 20, 6, "topic", 9, [topic("Technology")])
        assessment(session, 21, 2, "topic", 9, [topic()])
        session.flush()
        session.get(AnalysisRow, identity("ana", 21)).configuration_hash = "1" * 64
        # Domain-level visibility must also gate an otherwise earlier model row.
        assessment(session, 22, 5, "topic", 9, [topic("Future Document")])
    values = client.get("/api/v1/topics", params={"as_of": at(15).isoformat()}).json()["data"]
    assert len(values) == 5
    assert any(value["label"] == "Technology" for value in values)
    assert not any(value["label"] == "Future Document" for value in values)
    lower = [value for value in values if value["label"] == "technology"]
    assert len({value["topic_id"] for value in lower}) == 3


def test_latest_analysis_ties_are_stable_and_keep_first_document_sentiment(corpus):
    client, repository = corpus
    with repository.sessions.begin() as session:
        assessment(session, 30, 1, "topic", 5, [topic("Tie Winner")])
        assessment(
            session,
            31,
            2,
            "sentiment",
            8,
            [
                sentiment("negative", identity("ent", 1)),
                sentiment("neutral"),
                sentiment("positive"),
            ],
        )
    topics = client.get("/api/v1/topics", params={"as_of": at(15).isoformat()}).json()["data"]
    assert next(value for value in topics if value["label"] == "Tie Winner")["document_count"] == 1
    report = client.get(
        "/api/v1/analytics",
        params={"start": at(1).isoformat(), "end": at(15).isoformat(), "as_of": at(15).isoformat()},
    ).json()["data"]
    assert {value["label"]: value["document_count"] for value in report["sentiment"]} == {
        "positive": 1,
        "neutral": 2,
        "negative": 0,
        "mixed": 0,
    }


def test_discovery_first_seen_null_tail_literal_search_and_utc_filter_replay(corpus):
    client, repository = corpus
    with repository.sessions.begin() as session:
        seed_doc(session, 7, None, 7)
    first_seen = client.get(
        "/api/v1/discovery", params={"as_of": at(15).isoformat(), "order": "first_seen_at"}
    ).json()["data"]
    assert [value["document"]["document_id"] for value in first_seen] == [
        identity("doc", i) for i in (4, 7, 3, 2, 1, 6)
    ]
    params = {
        "as_of": at(15).isoformat(),
        "limit": 1,
        "start": "2026-01-01T05:30:00+05:30",
        "end": at(15).isoformat(),
    }
    first = client.get("/api/v1/discovery", params=params).json()
    continuation = client.get(
        "/api/v1/discovery",
        params={
            "cursor": first["pagination"]["next_cursor"],
            "start": at(1).isoformat(),
            "end": at(15).isoformat(),
            "limit": 1,
        },
    )
    assert continuation.status_code == 200
    seen = []
    page = client.get("/api/v1/discovery", params={"as_of": at(15).isoformat(), "limit": 1}).json()
    while True:
        seen += page["data"]
        if not page["pagination"]["has_more"]:
            break
        page = client.get(
            "/api/v1/discovery", params={"cursor": page["pagination"]["next_cursor"], "limit": 1}
        ).json()
    assert [value["document"]["document_id"] for value in seen[-2:]] == [
        identity("doc", 3),
        identity("doc", 7),
    ]
    assert client.get("/api/v1/discovery", params={"q": "%"}).json()["data"] == []
    report = client.get(
        "/api/v1/analytics",
        params={
            "start": at(1).isoformat(),
            "end": at(15).isoformat(),
            "as_of": at(15).isoformat(),
            "time_basis": "first_seen_at",
        },
    ).json()["data"]
    assert report["population_count"] == 6 and report["unknown_time_count"] == 0


def test_representative_sql_population_remains_bounded_with_revisions(corpus):
    client, repository = corpus
    with repository.sessions.begin() as session:
        session.execute(
            text("""
          INSERT INTO documents (document_id,ingestion_id,source_id,title,text,
            published_at,first_seen_at,ingested_at,created_at)
          SELECT 'doc_'||md5('coverage-'||g)::uuid,
            :ingestion,:source,'Original Synthetic Coverage '||g,'Original synthetic reporting.',
            '2026-01-03'::timestamptz,'2026-01-04'::timestamptz,
            '2026-01-04'::timestamptz,'2026-01-04'::timestamptz
          FROM generate_series(1,2000) g
        """),
            {"ingestion": identity("ing", 1), "source": identity("src", 1)},
        )
        session.execute(
            text("""
          INSERT INTO analyses (analysis_id,document_id,analysis_type,provider,model_name,
            model_version,configuration_hash,created_at,available_at,outputs)
          SELECT 'ana_'||md5('revision-'||g||'-'||r)::uuid,'doc_'||md5('coverage-'||g)::uuid,
            'topic','synthetic','topic-fixture','1',repeat('0',64),
            '2026-01-05'::timestamptz+r*interval '1 day',
            '2026-01-05'::timestamptz+r*interval '1 day',
            jsonb_build_array(jsonb_build_object('result_type','topic','label','technology',
              'confidence',0.8))
          FROM generate_series(1,2000) g CROSS JOIN generate_series(1,3) r
        """)
        )
        session.execute(
            text("""
          INSERT INTO analyses (analysis_id,document_id,analysis_type,provider,model_name,
            model_version,configuration_hash,created_at,available_at,outputs)
          SELECT 'ana_'||md5('sentiment-'||g)::uuid,'doc_'||md5('coverage-'||g)::uuid,
            'sentiment','synthetic','sentiment-fixture','1',repeat('0',64),
            '2026-01-08'::timestamptz,'2026-01-08'::timestamptz,
            jsonb_build_array(jsonb_build_object('result_type','sentiment','label','neutral',
              'score',0,'confidence',0.8,'entity_id',NULL))
          FROM generate_series(1,2000) g
        """)
        )
        session.execute(text("ANALYZE documents"))
        session.execute(text("ANALYZE analyses"))
    engine = repository.sessions.kw["bind"]
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("WITH "):
            statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", capture)
    params = {"as_of": at(15).isoformat()}
    timings = {}
    try:
        for path in ("topics", "discovery", "analytics"):
            query = (
                {**params, "start": at(1).isoformat(), "end": at(15).isoformat()}
                if path == "analytics"
                else params
            )
            started = perf_counter()
            response = client.get("/api/v1/" + path, params=query)
            timings[path] = round((perf_counter() - started) * 1000, 2)
            assert response.status_code == 200, response.text
            value = response.json()["data"]
            if path == "topics":
                assert (
                    next(
                        v
                        for v in value
                        if v["label"] == "technology" and v["model"]["model_version"] == "1"
                    )["document_count"]
                    == 2002
                )
            elif path == "discovery":
                assert len(value) == 25 and response.json()["pagination"]["has_more"]
            else:
                assert value["population_count"] == 2004 and value["classified_count"] == 2003
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    plans = []
    with engine.connect() as connection:
        for statement, parameters in statements:
            plan = connection.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters
            ).scalar_one()[0]
            plans.append(
                {
                    "execution_ms": plan["Execution Time"],
                    "planning_ms": plan["Planning Time"],
                    "node": plan["Plan"]["Node Type"],
                }
            )
    print(
        "Representative Original Synthetic Corpus: "
        + json.dumps({"documents": 2006, "analyses": 8010, "http_ms": timings, "sql_plans": plans})
    )


def test_aggregate_distributions_are_bounded_and_other_counts_preserve_denominators(corpus):
    client, repository = corpus
    with repository.sessions.begin() as session:
        session.execute(
            text("""
          INSERT INTO sources (source_id,name,kind,created_at)
          SELECT 'src_'||md5('distribution-'||g)::uuid,'Original Synthetic Publisher '||g,
            'upload','2026-01-01'::timestamptz FROM generate_series(1,110) g
        """)
        )
        session.execute(
            text("""
          INSERT INTO ingestions (ingestion_id,source_id,raw_object_id,
            first_seen_at,ingested_at,idempotency_key)
          SELECT 'ing_'||md5('distribution-'||g)::uuid,
            'src_'||md5('distribution-'||g)::uuid,:raw,
            '2026-01-04'::timestamptz,'2026-01-04'::timestamptz,'distribution-'||g
          FROM generate_series(1,110) g
        """),
            {"raw": identity("raw", 1)},
        )
        session.execute(
            text("""
          INSERT INTO documents (document_id,ingestion_id,source_id,title,text,
            published_at,first_seen_at,ingested_at,created_at)
          SELECT 'doc_'||md5('distribution-'||g)::uuid,
            'ing_'||md5('distribution-'||g)::uuid,'src_'||md5('distribution-'||g)::uuid,
            'Original Synthetic Story','Original synthetic reporting.',
            '2026-01-03'::timestamptz,'2026-01-04'::timestamptz,
            '2026-01-04'::timestamptz,'2026-01-04'::timestamptz
          FROM generate_series(1,110) g
        """)
        )
        session.execute(
            text("""
          INSERT INTO analyses (analysis_id,document_id,analysis_type,provider,model_name,
            model_version,configuration_hash,created_at,available_at,outputs)
          SELECT 'ana_'||md5('distribution-'||g)::uuid,
            'doc_'||md5('distribution-'||g)::uuid,'sentiment','synthetic',
            'distribution-fixture-'||g,'1',repeat('0',64),
            '2026-01-08'::timestamptz,'2026-01-08'::timestamptz,
            jsonb_build_array(jsonb_build_object('result_type','sentiment','label','neutral',
              'score',0,'confidence',0.8,'entity_id',NULL))
          FROM generate_series(1,110) g
        """)
        )
    report = client.get(
        "/api/v1/analytics",
        params={"start": at(1).isoformat(), "end": at(15).isoformat(), "as_of": at(15).isoformat()},
    ).json()["data"]
    assert len(report["sources"]) == len(report["models"]) == 100
    assert (
        sum(value["document_count"] for value in report["sources"]) + report["sources_other_count"]
        == report["population_count"]
        == 114
    )
    assert (
        sum(value["document_count"] for value in report["models"]) + report["models_other_count"]
        == report["classified_count"]
        == 113
    )
    source_id = identity("src", 1)
    filtered = client.get(
        "/api/v1/analytics",
        params={
            "start": at(1).isoformat(),
            "end": at(15).isoformat(),
            "as_of": at(15).isoformat(),
            "source_id": source_id,
        },
    ).json()["data"]
    assert filtered["population_count"] == 4
