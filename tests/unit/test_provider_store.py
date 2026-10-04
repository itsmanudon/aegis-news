"""Real persistence seams using synthetic acquisition data; no document SQL writers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from aegis.providers.models import ExternalNewsRecord, ProviderRun, YouTubeReference
from aegis.providers.persistence import (
    ArticleAliasRow,
    ProviderArticleRow,
    ProviderEvidenceRow,
    ProviderRunRow,
    ProviderStore,
    YouTubeReferenceRow,
)


def store():
    engine = create_engine("sqlite://")
    for table in (
        ProviderArticleRow,
        ArticleAliasRow,
        ProviderEvidenceRow,
        ProviderRunRow,
        YouTubeReferenceRow,
    ):
        table.__table__.create(engine)
    return ProviderStore(sessionmaker(engine, expire_on_commit=False))


def article(**changes):
    return ExternalNewsRecord(
        provider="gnews",
        provider_item_id="one",
        title="Atlas launches a new laboratory",
        description="Synthetic development content.",
        article_url="https://publisher.test/a",
        publisher_name="Publisher",
        **changes,
    )


def test_dedupe_retains_provider_evidence_and_frozen_submission_on_repeat():
    database = store()
    first, duplicate = database.prepare(article(), "src_00000000-0000-0000-0000-000000000001")
    assert not duplicate
    database.submitted(first.article_id, "ingestion-test")
    changed = article().model_copy(
        update={"description": "Changed snippet", "image_url": "https://images.test/a.jpg"}
    )
    repeated, duplicate = database.prepare(changed, "src_00000000-0000-0000-0000-000000000001")
    assert duplicate
    assert repeated.request == first.request
    cross = article().model_copy(
        update={
            "provider": "newsdata",
            "provider_item_id": "two",
            "article_url": "https://publisher.test/a?utm_source=second",
        }
    )
    merged, duplicate = database.prepare(cross, "src_00000000-0000-0000-0000-000000000002")
    assert duplicate
    assert merged.article_id == first.article_id
    with database.sessions() as session:
        assert len(list(session.scalars(select(ProviderArticleRow)))) == 1
        assert len(list(session.scalars(select(ProviderEvidenceRow)))) == 2


def test_headline_dedupe_and_interrupted_submission_can_resume():
    database = store()
    first, _ = database.prepare(article(), "src_00000000-0000-0000-0000-000000000001")
    second = article().model_copy(
        update={
            "provider": "newsapi",
            "provider_item_id": None,
            "article_url": "https://other.test/story",
            "title": "ATLAS launches a new laboratory!",
        }
    )
    resumed, duplicate = database.prepare(second, "src_00000000-0000-0000-0000-000000000002")
    assert duplicate and resumed.article_id == first.article_id
    assert resumed.workflow_id is None
    assert resumed.request == first.request


def test_youtube_expiry_and_refresh_replaces_metadata_and_removes_deleted_videos():
    database = store()
    now = datetime.now(UTC)
    reference = YouTubeReference(
        video_id="abcdefghijk",
        title="Synthetic video",
        channel_id="channel-one",
        channel_title="News",
        youtube_url="https://www.youtube.com/watch?v=abcdefghijk",
        last_refreshed_at=now,
        expires_at=now + timedelta(days=29),
    )
    database.videos([reference])
    assert len(database.video_page(10, None, now)) == 1
    database.videos([reference.model_copy(update={"title": "Updated title"})])
    assert database.video_page(10, None, now)[0].title == "Updated title"
    assert database.prune(now + timedelta(days=30)) == 1
    assert database.video_page(10, None, now + timedelta(days=30)) == []
    database.videos([reference])
    database.refresh_videos([reference.video_id], [])
    assert database.video_page(10, None, now) == []


def test_restart_marks_only_unfinished_runs_interrupted():
    database = store()
    now = datetime.now(UTC)
    database.run(ProviderRun(run_id="unfinished", created_at=now, status="running"))
    database.run(ProviderRun(run_id="finished", created_at=now, status="submitted"))
    database.interrupt_runs()
    assert database.get_run("unfinished").status == "interrupted"
    assert database.get_run("finished").status == "submitted"
