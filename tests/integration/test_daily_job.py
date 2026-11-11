"""The daily job end to end: a throwaway Temporal server, the real workflow, PostgreSQL and
the object store. Runs where a Temporal CLI is on the PATH (or AEGIS_TEMPORAL_CLI)."""

import os
import shutil
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
