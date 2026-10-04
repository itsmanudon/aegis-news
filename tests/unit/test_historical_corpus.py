"""The development loader must preserve inputs and recover through real API boundaries."""

import csv
import hashlib
import importlib
import json

import httpx
import pytest


def corpus_module():
    return importlib.import_module("scripts.load_historical_corpus")


def csv_file(tmp_path, rows):
    path = tmp_path / "train.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)
    return path


def test_conversion_separates_source_category_and_unknown_publication(tmp_path):
    corpus = corpus_module().prepare_csv(
        csv_file(tmp_path, [[3, "Company headline", r"Meaningful\ndescription"]]), 1
    )
    record = corpus.records[0]
    assert record.article == {
        "title": "Company headline",
        "text": "Meaningful\ndescription",
        "language": "en",
        "published_at": None,
    }
    assert record.category == "Business"
    assert "category" not in record.request("src_00000000-0000-0000-0000-000000000001").model_dump()
    assert "category" not in json.loads(record.content)


def test_limits_keep_original_ordinals_and_keys_across_prefix_runs(tmp_path):
    module = corpus_module()
    path = csv_file(tmp_path, [[1, "One", "Body one"], [2, "Two", "Body two"]])
    small, large = module.prepare_csv(path, 1), module.prepare_csv(path, 5)
    assert small.raw_records == large.raw_records == 2
    assert len(small.records) == 1
    assert len(large.records) == 2
    assert small.records[0].key == large.records[0].key
    assert large.records[1].ordinal == 2
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert small.records[0].key == f"historical:ag-news-v3:train:{digest}:1"
    with pytest.raises(ValueError):
        module.prepare_csv(path, 0)


def test_malformed_duplicate_and_oversize_rows_do_not_abort_selection(tmp_path):
    module = corpus_module()
    rows = [
        [1, "One", "Body"],
        [2, "One", "Body"],  # Exact same article, conflicting category stays source-only.
        [1, "", "Body"],
        [9, "Bad class", "Body"],
        [3, "Missing column"],
        [4, "Too big", "x" * (256 * 1024)],
        [2, "Last", "Valid body"],
    ]
    corpus = module.prepare_csv(csv_file(tmp_path, rows), 2)
    assert [r.ordinal for r in corpus.records] == [1, 7]
    assert corpus.considered == 7
    assert len(corpus.skipped) == 5
    assert corpus.skipped[0]["reason"] == "exact_duplicate"


def test_invalid_utf8_row_is_skipped(tmp_path):
    path = tmp_path / "train.csv"
    path.write_bytes(b'1,"Bad","invalid\xff"\n2,"Valid","Body"\n')
    corpus = corpus_module().prepare_csv(path, 1)
    assert corpus.records[0].ordinal == 2
    assert corpus.skipped[0]["reason"] == "invalid_utf8"


def test_csv_field_error_does_not_discard_following_valid_rows(tmp_path):
    path = csv_file(tmp_path, [[1, "Oversize", "x" * 600000], [2, "Valid", "Body"]])
    corpus = corpus_module().prepare_csv(path, 1)
    assert corpus.records[0].ordinal == 2
    assert len(corpus.skipped) == 1


def test_download_is_mocked_verified_and_reused(tmp_path, monkeypatch):
    module = corpus_module()
    content = b'1,"Headline","Body"\n'
    digest = hashlib.sha256(content).hexdigest()
    calls = []

    def retrieve(url, path):
        calls.append(url)
        path.write_bytes(content)

    monkeypatch.setattr(module.urllib.request, "urlretrieve", retrieve)
    target = tmp_path / "train.csv"
    module.acquire(target, "https://example.org/train.csv", digest)
    module.acquire(target, "https://example.org/train.csv", digest)
    assert len(calls) == 1
    target.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        module.acquire(target, "https://example.org/train.csv", digest)


@pytest.mark.asyncio
async def test_resume_rechecks_workflows_and_progress_accounts_existing(tmp_path):
    module = corpus_module()
    corpus = module.prepare_csv(csv_file(tmp_path, [[1, "One", "Body"], [2, "Two", "Body two"]]), 2)
    runs = {}
    posted = []

    def server(request):
        if request.url.path == "/ready":
            return httpx.Response(200, json={"data": {"status": "ready"}})
        if request.url.path == "/api/v1/sources":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "source_id": "src_00000000-0000-0000-0000-000000000001",
                            "name": module.SOURCE_NAME,
                        }
                    ],
                    "pagination": {"has_more": False},
                },
            )
        if request.url.path.startswith("/api/v1/sources/"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "source_id": "src_00000000-0000-0000-0000-000000000001",
                        "name": module.SOURCE_NAME,
                    }
                },
            )
        if request.url.path == "/api/v1/ingestions/batch":
            items = json.loads(request.content)["items"]
            submissions = []
            for item in items:
                parsed = module.IngestionRequest.model_validate(item)
                workflow = module.workflow_identity(parsed)
                posted.append(item["idempotency_key"])
                runs[workflow] = {
                    "status": "COMPLETED",
                    "result": {
                        "document_id": "doc_00000000-0000-0000-0000-000000000001",
                        "analyze_entities": "completed",
                    },
                }
                submissions.append({"workflow_id": workflow})
            return httpx.Response(202, json={"data": {"submissions": submissions}})
        workflow = request.url.path.rsplit("/", 1)[-1]
        return (
            httpx.Response(200, json={"data": runs[workflow]})
            if workflow in runs
            else httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})
        )

    async with httpx.AsyncClient(
        base_url="http://localhost", transport=httpx.MockTransport(server)
    ) as client:
        api = module.Api(client, lambda: "test-only", requests_per_second=10000)
        first = await module.load(
            corpus, api, tmp_path / "state.json", batch_size=1, concurrency=1, poll_interval=0.001
        )
        second = await module.load(
            corpus, api, tmp_path / "state.json", batch_size=2, concurrency=1, poll_interval=0.001
        )
    assert first["submitted"] == first["completed"] == 2
    assert first["existing"] == first["failed"] == first["pending"] == 0
    assert second["submitted"] == second["failed"] == second["pending"] == 0
    assert second["completed"] == second["existing"] == 2
    assert len(posted) == 2


@pytest.mark.asyncio
async def test_partial_batch_timeout_reuses_same_request_without_duplicates():
    module = corpus_module()
    attempts = 0

    def server(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("controlled lost acknowledgement", request=request)
        return httpx.Response(202, json={"data": {"submissions": [{"workflow_id": "same"}]}})

    async with httpx.AsyncClient(
        base_url="http://localhost", transport=httpx.MockTransport(server)
    ) as client:
        api = module.Api(client, lambda: "test-only", requests_per_second=10000, retry_delay=0)
        value = await api.request(
            "POST", "/api/v1/ingestions/batch", {"items": [{"idempotency_key": "stable"}]}
        )
    assert value["data"]["submissions"][0]["workflow_id"] == "same"
    assert attempts == 2


class WorkflowServer:
    """Only the external API is replaced; conversion, IDs, checkpoints and counters are real."""

    source = "src_00000000-0000-0000-0000-000000000001"

    def __init__(self):
        self.runs = {}
        self.posts = 0
        self.interrupt_poll = False
        self.fail_workflow = False
        self.peak_active = 0

    def __call__(self, request):
        module = corpus_module()
        path = request.url.path
        if path == "/ready":
            return httpx.Response(200, json={"data": {"status": "ready"}})
        if path == "/api/v1/sources":
            return httpx.Response(
                200,
                json={
                    "data": [{"source_id": self.source, "name": module.SOURCE_NAME}],
                    "pagination": {"has_more": False},
                },
            )
        if path.startswith("/api/v1/sources/"):
            return httpx.Response(200, json={"data": {"source_id": self.source}})
        if path == "/api/v1/ingestions/batch":
            submissions = []
            for item in json.loads(request.content)["items"]:
                workflow = module.workflow_identity(module.IngestionRequest.model_validate(item))
                self.runs[workflow] = {"status": "RUNNING", "result": None}
                submissions.append({"workflow_id": workflow})
                self.posts += 1
            self.peak_active = max(
                self.peak_active, sum(r["status"] == "RUNNING" for r in self.runs.values())
            )
            return httpx.Response(202, json={"data": {"submissions": submissions}})
        workflow = path.rsplit("/", 1)[-1]
        if workflow not in self.runs:
            return httpx.Response(404)
        if self.interrupt_poll:
            self.interrupt_poll = False
            return httpx.Response(401)
        if self.runs[workflow]["status"] == "FAILED":
            return httpx.Response(200, json={"data": self.runs[workflow]})
        self.runs[workflow] = {
            "status": "FAILED" if self.fail_workflow else "COMPLETED",
            "result": {"document_id": "doc_00000000-0000-0000-0000-000000000001"},
        }
        return httpx.Response(200, json={"data": self.runs[workflow]})


@pytest.mark.asyncio
async def test_lost_poll_preserves_checkpoint_and_rerun_reuses_started_work(tmp_path):
    module, server = corpus_module(), WorkflowServer()
    corpus = module.prepare_csv(csv_file(tmp_path, [[1, "One", "Body"], [2, "Two", "Body two"]]), 2)
    server.interrupt_poll = True
    async with httpx.AsyncClient(
        base_url="http://localhost", transport=httpx.MockTransport(server)
    ) as client:
        api = module.Api(client, lambda: "test-only", requests_per_second=10000)
        with pytest.raises(ExceptionGroup):
            await module.load(corpus, api, tmp_path / "state.json", batch_size=2)
        checkpoint = json.loads((tmp_path / "state.json").read_text())
        assert all(row["submitted"] for row in checkpoint["records"].values())
        resumed = await module.load(corpus, api, tmp_path / "state.json", batch_size=2)
    assert resumed["completed"] == resumed["existing"] == 2
    assert resumed["submitted"] == resumed["pending"] == 0
    assert server.posts == 2


@pytest.mark.asyncio
async def test_failed_workflow_reported_and_retried_on_next_run(tmp_path):
    module, server = corpus_module(), WorkflowServer()
    corpus = module.prepare_csv(csv_file(tmp_path, [[1, "One", "Body"]]), 1)
    server.fail_workflow = True
    async with httpx.AsyncClient(
        base_url="http://localhost", transport=httpx.MockTransport(server)
    ) as client:
        api = module.Api(client, lambda: "test-only", requests_per_second=10000)
        failed = await module.load(corpus, api, tmp_path / "state.json")
        assert failed["failed"] == 1
        assert failed["completed"] == failed["pending"] == 0
        assert failed["failures"][0]["error"] == "Temporal FAILED"
        server.fail_workflow = False
        resumed = await module.load(corpus, api, tmp_path / "state.json")
    assert resumed["submitted"] == resumed["completed"] == 1
    assert resumed["failed"] == 0


@pytest.mark.asyncio
async def test_inflight_batches_remain_bounded(tmp_path):
    module, server = corpus_module(), WorkflowServer()
    corpus = module.prepare_csv(
        csv_file(tmp_path, [[1, str(i), "Body " + str(i)] for i in range(8)]), 8
    )
    async with httpx.AsyncClient(
        base_url="http://localhost", transport=httpx.MockTransport(server)
    ) as client:
        result = await module.load(
            corpus,
            module.Api(client, lambda: "test-only", requests_per_second=10000),
            tmp_path / "state.json",
            batch_size=2,
            concurrency=2,
        )
    assert result["completed"] == 8
    assert server.peak_active <= 4
