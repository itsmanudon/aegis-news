"""The daily job end to end: a throwaway Temporal server, the real workflow, PostgreSQL and
the object store. Runs where a Temporal CLI is on the PATH (or AEGIS_TEMPORAL_CLI)."""

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.engine import make_url

from aegis.jobs.daily import run
from aegis.persistence.models import AnalysisRow, Base, DocumentRow
from aegis.providers.models import ExternalNewsRecord, FetchBatch
from aegis.providers.persistence import ProviderArticleRow
from aegis.security.persistence import SignedManifestRow
from aegis.settings import Settings

CLI = shutil.which(os.environ.get("AEGIS_TEMPORAL_CLI", "temporal"))
pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.skipif(not CLI, reason="needs the Temporal CLI"),
]


class Headlines:
    """Two synthetic articles, as a provider adapter would return them."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, query, limit, country=None):
        self.calls += 1
        return FetchBatch(
            records=tuple(
                ExternalNewsRecord(
                    provider="newsdata",
                    provider_item_id=f"job-{n}",
                    title=f"Atlas Labs reports quarter {n}",
                    description="Synthetic description for the daily job test.",
                    article_url=f"https://publisher.test/job/{n}",
                    publisher_name="Synthetic Publisher",
                )
                for n in (1, 2)
            ),
            requests=1,
        )


@pytest.fixture
def job_settings():
    url = os.environ.get("AEGIS_INGESTION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set AEGIS_INGESTION_TEST_DATABASE_URL to a disposable PostgreSQL database")
    schema = "daily_job_" + uuid4().hex
    root = create_engine(url)
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(scoped)
    Base.metadata.create_all(engine)
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    settings = Settings(
        _env_file=None,
        database_url=scoped.render_as_string(hide_password=False),
        s3_endpoint_url=os.environ.get("AEGIS_S3_ENDPOINT_URL", "http://localhost:9000"),
        newsdata_api_key="synthetic-key",
        temporal_cli_path=CLI,
        temporal_task_queue="daily-job-" + uuid4().hex,
        provenance_key_id="jobtest",
        provenance_signing_key=pem.decode(),
    )
    yield settings, engine
    engine.dispose()
    with root.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    root.dispose()


def count(engine, table):
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


async def test_runs_twice_and_after_an_interruption_without_duplicates(job_settings):
    settings, engine = job_settings
    adapter = Headlines()

    first = await run(settings, {"newsdata": adapter})
    assert first.ok, first
    assert (first.completed, first.already_done, first.failed) == (2, 0, ())
    assert count(engine, DocumentRow.__table__) == 2
    # Each document is signed once, with the key from the environment, and is in the feed.
    assert count(engine, SignedManifestRow.__table__) == 2
    with engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count())
                .where(DocumentRow.last_signed_at.is_(None))
                .select_from(DocumentRow.__table__)
            )
            == 0
        )
        assert set(connection.scalars(select(SignedManifestRow.key_id))) == {"jobtest"}
    analyses = count(engine, AnalysisRow.__table__)

    # A second run finds the same articles done and changes nothing.
    second = await run(settings, {"newsdata": adapter})
    assert second.ok, second
    assert (second.completed, second.already_done) == (0, 2)
    assert count(engine, DocumentRow.__table__) == 2
    assert count(engine, SignedManifestRow.__table__) == 2
    assert count(engine, AnalysisRow.__table__) == analyses

    # A run killed before it recorded completion: the article is submitted again, and the
    # workflow's stable identities make the repeat a no-op.
    with engine.begin() as connection:
        connection.execute(
            update(ProviderArticleRow.__table__)
            .where(ProviderArticleRow.__table__.c.title == "Atlas Labs reports quarter 1")
            .values(document_id=None)
        )
    third = await run(settings, {"newsdata": adapter})
    assert third.ok, third
    assert (third.completed, third.already_done) == (1, 1)
    assert count(engine, DocumentRow.__table__) == 2
    assert count(engine, SignedManifestRow.__table__) == 2
    assert count(engine, AnalysisRow.__table__) == analyses
    assert adapter.calls == 3


async def test_a_missing_cli_stops_the_job_before_anything_runs(job_settings):
    settings, engine = job_settings
    with pytest.raises(FileNotFoundError):
        await run(settings.model_copy(update={"temporal_cli_path": "no-such-temporal"}))
    assert count(engine, DocumentRow.__table__) == 0


class ByQuery:
    """One article per query plus one every query returns, as syndicated news does."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def fetch(self, query, limit, country=None):
        self.queries.append(query)
        n = len(self.queries)
        records = [
            ExternalNewsRecord(
                provider="newsdata",
                provider_item_id=f"query-{n}",
                title=f"Apple and Microsoft headline {n}",
                description="Synthetic description for the company search test.",
                article_url=f"https://publisher.test/query/{n}",
                publisher_name="Synthetic Publisher",
            ),
            ExternalNewsRecord(
                provider="newsdata",
                provider_item_id="shared",
                title="Nvidia shares rise",
                description="Synthetic description for the company search test.",
                article_url="https://publisher.test/shared",
                publisher_name="Synthetic Publisher",
            ),
        ]
        return FetchBatch(records=tuple(records), requests=1)


SEED = Path("data/instruments/stockviz.json")


async def test_company_searches_follow_the_general_query_without_duplicates(job_settings):
    settings, engine = job_settings
    settings = settings.model_copy(update={"job_company_file": SEED, "job_company_requests": 2})
    adapter = ByQuery()
    report = await run(settings, {"newsdata": adapter})
    assert report.ok, report
    assert adapter.queries[0] == settings.job_query
    assert adapter.queries[1:] == list(report.company_queries)
    assert len(report.company_queries) == 2 and len(report.company_runs) == 2
    # Three per-query articles and the shared one, each stored once.
    assert (report.completed, report.failed) == (4, ())
    assert count(engine, DocumentRow.__table__) == 4


async def test_company_searches_stop_at_the_daily_budget(job_settings):
    settings, engine = job_settings
    settings = settings.model_copy(
        update={
            "job_company_file": SEED,
            "job_company_requests": 3,
            # Each fetch reserves MAX_PAGES (3) requests before it starts: 1 + 3 <= 4,
            # then 2 + 3 > 4.
            "provider_daily_requests": {"newsdata": 4},
        }
    )
    adapter = ByQuery()
    report = await run(settings, {"newsdata": adapter})
    # The budget is expected, not a failure: the general query and one company search ran.
    assert report.ok, report
    assert len(adapter.queries) == 2
    errors = [o.error for r in report.company_runs for o in r.outcomes]
    assert errors == [None, "daily_budget_reached", "daily_budget_reached"]
