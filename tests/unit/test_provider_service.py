from aegis.providers.models import ExternalNewsRecord, FetchBatch, FetchOptions
from aegis.providers.service import ProviderRunner
from aegis.providers.transport import ProviderError
from aegis.settings import Settings


class MemoryStage:
    def __init__(self):
        self.rows = {}
        self.evidence = []
        self.runs = {}

    def known(self, record):
        return self.rows.get(record.title)

    def publisher(self, name, url):
        return None

    def prepare(self, record, source):
        from types import SimpleNamespace

        duplicate = record.title in self.rows
        row = self.rows.setdefault(
            record.title,
            SimpleNamespace(
                article_id=record.title,
                request={"source_id": source, "idempotency_key": "live:test:" + record.title},
                workflow_id=None,
            ),
        )
        self.evidence.append(record.provider)
        return row, duplicate

    def submitted(self, identity, workflow):
        self.rows[identity].workflow_id = workflow

    def run(self, report):
        self.runs[report.run_id] = report

    def videos(self, values):
        pass


class Gateway:
    def __init__(self):
        self.posts = []

    async def request(self, method, path, body=None):
        self.posts.append((path, body))
        if path == "/api/v1/sources":
            return {"source_id": "src_00000000-0000-0000-0000-000000000001"}
        return {"workflow_id": "ingestion-one"}


class Adapter:
    def __init__(self, name, failure=False):
        self.name, self.failure = name, failure

    async def fetch(self, query, limit, country):
        if self.failure:
            raise ProviderError("permission_or_quota")
        return FetchBatch(
            records=(
                ExternalNewsRecord(
                    provider=self.name,
                    provider_item_id="one",
                    title="Synthetic shared headline",
                    publisher_name="Publisher",
                    article_url="https://publisher.test/story",
                ),
            )
        )


async def test_failure_isolation_duplicate_evidence_and_idempotent_submission():
    stage, gateway = MemoryStage(), Gateway()
    runner = ProviderRunner(
        Settings(
            _env_file=None,
            newsdata_api_key="test-secret",
            gnews_api_key="test-secret",
            newsapi_api_key="test-secret",
        ),
        stage,
    )
    adapters = {
        "newsdata": Adapter("newsdata"),
        "gnews": Adapter("gnews"),
        "newsapi": Adapter("newsapi", True),
    }
    run = await runner.execute(
        ["newsdata", "gnews", "newsapi"], FetchOptions(limit=1), gateway, adapters
    )
    assert [o.status for o in run.outcomes] == ["submitted", "submitted", "failed"]
    assert sum(o.submitted for o in run.outcomes) == 1
    assert sum(o.duplicates for o in run.outcomes) == 1
    assert stage.evidence == ["newsdata", "gnews"]
    assert len([p for p, _ in gateway.posts if p == "/api/v1/ingestions"]) == 1
    again = await runner.execute(["newsdata"], FetchOptions(limit=1), gateway, adapters)
    assert again.outcomes[0].submitted == 0
    assert again.outcomes[0].duplicates == 1
    assert "test-secret" not in again.model_dump_json()


async def test_single_disabled_provider_is_reported_without_network_or_ingestion():
    stage, gateway = MemoryStage(), Gateway()
    runner = ProviderRunner(Settings(_env_file=None), stage)
    result = await runner.execute(["gnews"], FetchOptions(limit=1), gateway)
    assert len(result.outcomes) == 1
    assert result.outcomes[0].status == "disabled"
    assert stage.runs[result.run_id] == result
    assert not gateway.posts and not stage.rows
