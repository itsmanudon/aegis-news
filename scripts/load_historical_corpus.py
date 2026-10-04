"""Local AG News development data -> existing authenticated ingestion API/Temporal.

No repository, database or internal processing calls. Run as a module with uv run.
Downloaded/converted news text and local receipts belong only in ignored .data/.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from aegis.ingestion.importers import historical_record
from aegis.ingestion.inputs import MAX_CONTENT_BYTES, IngestionRequest
from aegis.ingestion.submissions import workflow_identity
from aegis.normalization.article import Article
from scripts.demo import compose_command

REVISION = "03836ce08fce38daac53e9b4255ef16e0b9f6303"
UPSTREAM = f"https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/{REVISION}/data/ag_news_csv/train.csv"
SHA256 = "76a0a2d2f92b286371fe4d4044640910a04a803fdd2538e0f3f29a5c6f6b672e"
SOURCE_NAME = "AG News Historical Development Corpus"
SOURCE_URL = "https://github.com/mhjabreel/CharCnn_Keras/tree/master/data/ag_news_csv"
CATEGORIES = {"1": "World", "2": "Sports", "3": "Business", "4": "Sci/Tech"}
TERMINAL = {"FAILED", "TIMED_OUT", "TERMINATED", "CANCELED"}


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def acquire(path: Path, url: str = UPSTREAM, expected_sha256: str = SHA256) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(".download")
        try:
            urllib.request.urlretrieve(url, temporary)
            if digest(temporary) != expected_sha256:
                raise ValueError("download checksum mismatch")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    if digest(path) != expected_sha256:
        raise ValueError("cached corpus checksum mismatch; inspect rather than overwrite it")


@dataclass(frozen=True)
class Record:
    ordinal: int
    article: dict[str, Any]
    category: str
    dataset_sha256: str

    @property
    def content(self) -> bytes:
        return json.dumps(self.article, ensure_ascii=False, sort_keys=True).encode("utf-8")

    @property
    def namespace(self) -> str:
        return f"historical:ag-news-v3:train:{self.dataset_sha256}"

    @property
    def key(self) -> str:
        return f"{self.namespace}:{self.ordinal}"

    def request(self, source_id: str) -> IngestionRequest:
        value = historical_record(self.content, source_id, self.namespace, self.ordinal)
        return value.model_copy(update={"correlation_id": "historical-ag-news"})


@dataclass
class Corpus:
    records: list[Record]
    dataset_sha256: str
    raw_records: int
    considered: int
    skipped: list[dict[str, Any]]


def prepare_csv(path: Path, limit: int) -> Corpus:
    if limit < 1:
        raise ValueError("limit must be positive")
    dataset_sha256 = digest(path)
    records: list[Record] = []
    skipped: list[dict[str, Any]] = []
    seen: set[bytes] = set()
    raw_records = considered = 0
    csv.field_size_limit(MAX_CONTENT_BYTES * 2)
    with path.open(encoding="utf-8-sig", errors="surrogateescape", newline="") as handle:
        reader = csv.reader(handle)
        ordinal = 0
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            except csv.Error:
                row = []
            ordinal += 1
            raw_records += 1
            if len(records) >= limit:
                continue
            considered += 1
            reason = "malformed_row"
            try:
                if len(row) != 3 or row[0] not in CATEGORIES:
                    raise ValueError(reason)
                row[1].encode("utf-8")
                row[2].encode("utf-8")
                article = Article(
                    title=row[1].replace("\\n", "\n"),
                    text=row[2].replace("\\n", "\n"),
                    language="en",
                    published_at=None,
                ).model_dump(mode="json")
                record = Record(ordinal, article, CATEGORIES[row[0]], dataset_sha256)
                content = record.content
                if len(content) > MAX_CONTENT_BYTES:
                    reason = "oversize"
                    raise ValueError(reason)
                if content in seen:
                    reason = "exact_duplicate"
                    raise ValueError(reason)
                seen.add(content)
                records.append(record)
            except UnicodeEncodeError:
                skipped.append({"ordinal": ordinal, "reason": "invalid_utf8"})
            except ValueError:
                skipped.append({"ordinal": ordinal, "reason": reason})
    return Corpus(records, dataset_sha256, raw_records, considered, skipped)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def export(corpus: Corpus, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (
        (directory / "articles.jsonl").open("wb") as articles,
        (directory / "metadata.jsonl").open("w", encoding="utf-8") as metadata,
    ):
        for row in corpus.records:
            articles.write(row.content + b"\n")
            metadata.write(
                json.dumps({"ordinal": row.ordinal, "key": row.key, "category": row.category})
                + "\n"
            )
    write_json(
        directory / "dataset-receipt.json",
        {
            "upstream": UPSTREAM,
            "revision": REVISION,
            "sha256": corpus.dataset_sha256,
            "raw_records": corpus.raw_records,
            "considered": corpus.considered,
            "selected": len(corpus.records),
            "skipped": corpus.skipped,
            "purpose": "Non-commercial local development; not Gold evaluation data",
        },
    )


class ApiError(RuntimeError):
    def __init__(self, status: int, path: str) -> None:
        self.status = status
        super().__init__(f"API request failed: {path} (HTTP {status}); no payload/token logged")


class DevToken:
    """Refresh five-minute identities using the supported local Docker issuer."""

    def __init__(self, token_env: str | None = None) -> None:
        self.token_env = token_env
        self.value = ""
        self.expires = 0.0

    def __call__(self) -> str:
        if self.token_env:
            value = os.environ.get(self.token_env, "")
            if not value:
                raise ValueError("configured token environment variable is empty")
            return value
        if time.monotonic() >= self.expires:
            result = subprocess.run(
                compose_command(
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "scripts/security_dev.py",
                    "token",
                    "--key-id",
                    "local",
                    "--role",
                    "admin",
                    "--subject",
                    "historical-corpus-loader",
                ),
                check=True,
                capture_output=True,
                text=True,
            )
            self.value = result.stdout.strip()
            self.expires = time.monotonic() + 240
        return self.value


class Api:
    def __init__(
        self,
        client: httpx.AsyncClient,
        token: Callable[[], str],
        *,
        requests_per_second: float = 12,
        retry_delay: float = 1,
    ) -> None:
        self.client, self.token = client, token
        self.spacing = 1 / requests_per_second
        self.retry_delay = retry_delay
        self.lock = asyncio.Lock()
        self.next_request = 0.0
        self.requests = self.retries = 0
        self.response_seconds: list[float] = []

    async def request(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        for attempt in range(7):
            async with self.lock:
                await asyncio.sleep(max(0, self.next_request - time.monotonic()))
                self.next_request = time.monotonic() + self.spacing
                token = await asyncio.to_thread(self.token)
            started = time.monotonic()
            status = 0
            self.requests += 1
            try:
                response = await self.client.request(
                    method, path, json=body, headers={"Authorization": "Bearer " + token}
                )
                self.response_seconds.append(time.monotonic() - started)
                status = response.status_code
                if response.is_success:
                    value: dict[str, Any] = response.json()
                    return value
                if status not in {429, 500, 502, 503, 504}:
                    raise ApiError(status, path)
            except httpx.RequestError:
                pass
            if attempt == 6 or (method == "POST" and path == "/api/v1/sources"):
                raise ApiError(status, path)
            self.retries += 1
            await asyncio.sleep(min(30, self.retry_delay * 2**attempt))
        raise AssertionError("unreachable")


async def source_id(api: Api, saved: str | None) -> str:
    if saved:
        return str((await api.request("GET", "/api/v1/sources/" + saved))["data"]["source_id"])
    matches: list[str] = []
    path = "/api/v1/sources?limit=100"
    while True:
        page = await api.request("GET", path)
        matches.extend(s["source_id"] for s in page["data"] if s["name"] == SOURCE_NAME)
        if not page["pagination"]["has_more"]:
            break
        path = "/api/v1/sources?limit=100&cursor=" + page["pagination"]["next_cursor"]
    if len(matches) > 1:
        raise ValueError("multiple corpus sources: select one explicitly with --source-id")
    if matches:
        return str(matches[0])
    # Source creation has no idempotency contract: never blindly retry this POST.
    return str(
        (
            await api.request(
                "POST",
                "/api/v1/sources",
                {
                    "name": SOURCE_NAME,
                    "kind": "upload",
                    "url": SOURCE_URL,
                },
            )
        )["data"]["source_id"]
    )


async def load(
    corpus: Corpus,
    api: Api,
    state_path: Path,
    *,
    batch_size: int = 10,
    concurrency: int = 1,
    poll_interval: float = 2,
    workflow_timeout: float = 900,
    saved_source: str | None = None,
) -> dict[str, Any]:
    if not 1 <= batch_size <= 20 or not 1 <= concurrency <= 4 or poll_interval <= 0:
        raise ValueError("batch size 1..20, concurrency 1..4 and positive poll interval required")
    if (await api.request("GET", "/ready"))["data"]["status"] != "ready":
        raise ValueError("API not ready")
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state and (
        state["dataset_sha256"] != corpus.dataset_sha256
        or state["api_url"] != str(api.client.base_url)
    ):
        raise ValueError("checkpoint belongs to a different dataset or API")
    identity = await source_id(api, saved_source or state.get("source_id"))
    state.update(
        dataset_sha256=corpus.dataset_sha256, api_url=str(api.client.base_url), source_id=identity
    )
    entries: dict[str, dict[str, Any]] = state.setdefault("records", {})
    selected = {r.key for r in corpus.records}
    for row in corpus.records:
        entries[row.key] = {
            "ordinal": row.ordinal,
            "status": "pending",
            "existing": False,
            "submitted": False,
            "workflow_id": workflow_identity(row.request(identity)),
        }
    started = last_progress = time.monotonic()

    def summary() -> dict[str, Any]:
        values = [entries[k] for k in selected]
        elapsed = time.monotonic() - started
        return {
            "dataset_sha256": corpus.dataset_sha256,
            "source_id": identity,
            "raw_records": corpus.raw_records,
            "considered": corpus.considered,
            "requested": len(values),
            "submitted": sum(v["submitted"] for v in values),
            "completed": sum(v["status"] == "completed" for v in values),
            "existing": sum(v["existing"] for v in values),
            "skipped": len(corpus.skipped),
            "failed": sum(v["status"] == "failed" for v in values),
            "pending": sum(v["status"] == "pending" for v in values),
            "elapsed_seconds": elapsed,
            "new_records_per_minute": 60
            * sum(v["status"] == "completed" and v["submitted"] for v in values)
            / elapsed
            if elapsed > 0
            else None,
            "api_requests": api.requests,
            "api_retries": api.retries,
            "api_response_median_ms": statistics.median(api.response_seconds) * 1000
            if api.response_seconds
            else None,
            "api_response_p95_ms": sorted(api.response_seconds)[
                math.ceil(0.95 * len(api.response_seconds)) - 1
            ]
            * 1000
            if api.response_seconds
            else None,
            "unavailable_stages": {
                stage: sum(stage in v.get("degraded_stages", []) for v in values)
                for stage in (
                    "analyze_entities",
                    "analyze_topics",
                    "analyze_sentiment",
                    "generate_embedding",
                    "resolve_entities",
                    "extract_events",
                )
            },
            "failures": [v for v in values if v["status"] != "completed"],
        }

    def checkpoint(force: bool = False) -> None:
        nonlocal last_progress
        write_json(state_path, state)
        if force or time.monotonic() - last_progress >= 15:
            report = summary()
            print(
                json.dumps(
                    {
                        k: report[k]
                        for k in (
                            "requested",
                            "submitted",
                            "completed",
                            "existing",
                            "failed",
                            "pending",
                        )
                    }
                ),
                flush=True,
            )
            last_progress = time.monotonic()

    async def status(row: Record) -> dict[str, Any] | None:
        try:
            return dict(
                (
                    await api.request(
                        "GET", "/api/v1/ingestion-runs/" + entries[row.key]["workflow_id"]
                    )
                )["data"]
            )
        except ApiError as exc:
            if exc.status == 404:
                return None
            raise

    def completed(row: Record, run: dict[str, Any]) -> None:
        result = run["result"]
        stages = (
            "analyze_entities",
            "analyze_topics",
            "analyze_sentiment",
            "generate_embedding",
            "resolve_entities",
            "extract_events",
        )
        entry = entries[row.key]
        entry.update(status="completed", document_id=result["document_id"])
        entry["degraded_stages"] = [s for s in stages if result.get(s) != "completed"]

    async def batch(rows: list[Record]) -> None:
        fresh, pending = [], []
        for row in rows:
            run = await status(row)
            if run is not None and run["status"] not in TERMINAL:
                entries[row.key]["existing"] = True
                if run["status"] == "COMPLETED":
                    completed(row, run)
                else:
                    pending.append(row)
            else:
                fresh.append(row)
        checkpoint()
        if fresh:
            try:
                response = await api.request(
                    "POST",
                    "/api/v1/ingestions/batch",
                    {
                        "items": [r.request(identity).model_dump(mode="json") for r in fresh],
                    },
                )
                returned = response["data"]["submissions"]
                if len(returned) != len(fresh):
                    raise ValueError("batch response length mismatch")
                for row, submission in zip(fresh, returned, strict=True):
                    if submission["workflow_id"] != entries[row.key]["workflow_id"]:
                        raise ValueError("unexpected workflow identity")
                    entries[row.key]["submitted"] = True
                    pending.append(row)
            except ApiError as exc:
                if exc.status in {401, 403}:
                    raise
                for row in fresh:
                    entries[row.key]["error"] = str(exc)
                    # An exhausted timeout/503 might have submitted a partial batch.
                    if exc.status in {0, 429, 500, 502, 503, 504}:
                        pending.append(row)
                    else:
                        entries[row.key]["status"] = "failed"
        checkpoint()
        deadline = time.monotonic() + workflow_timeout
        while pending and time.monotonic() < deadline:
            remaining = []
            for row in pending:
                run = await status(row)
                if run is None or run["status"] not in TERMINAL | {"COMPLETED"}:
                    remaining.append(row)
                elif run["status"] == "COMPLETED":
                    completed(row, run)
                else:
                    entries[row.key].update(status="failed", error="Temporal " + run["status"])
            pending = remaining
            if pending:
                if time.monotonic() - last_progress >= 15:
                    checkpoint()
                await asyncio.sleep(poll_interval)
        checkpoint()

    queue: asyncio.Queue[list[Record]] = asyncio.Queue()
    for offset in range(0, len(corpus.records), batch_size):
        queue.put_nowait(corpus.records[offset : offset + batch_size])

    async def worker() -> None:
        while not queue.empty():
            await batch(queue.get_nowait())

    try:
        async with asyncio.TaskGroup() as group:
            for _ in range(concurrency):
                group.create_task(worker())
    finally:
        checkpoint(force=True)
        write_json(state_path.with_name("load-report.json"), summary())
    return summary()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrent batches; maximum in-flight = batch-size * concurrency",
    )
    parser.add_argument("--poll-interval", type=float, default=2)
    parser.add_argument("--api-url", default="http://127.0.0.1:38000")
    parser.add_argument("--data-dir", type=Path, default=Path(".data/historical/ag_news"))
    parser.add_argument(
        "--csv", type=Path, help="Use a local AG News-format CSV without downloading"
    )
    parser.add_argument("--source-id")
    parser.add_argument(
        "--token-env", help="Existing token environment variable; never a CLI token"
    )
    args = parser.parse_args()
    if urlsplit(args.api_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("this development loader is restricted to a loopback API")
    csv_path = args.csv or args.data_dir / "train.csv"
    if args.csv is None:
        acquire(csv_path)
    corpus = prepare_csv(csv_path, args.limit)
    export(corpus, args.data_dir)
    print(
        json.dumps(
            {
                "raw_records": corpus.raw_records,
                "selected": len(corpus.records),
                "skipped": len(corpus.skipped),
                "worker_profile": "use configured offline worker",
            }
        ),
        flush=True,
    )

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=args.api_url, timeout=30) as client:
            return await load(
                corpus,
                Api(client, DevToken(args.token_env)),
                args.data_dir / "state.json",
                batch_size=args.batch_size,
                concurrency=args.concurrency,
                poll_interval=args.poll_interval,
                saved_source=args.source_id,
            )

    try:
        report = asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted. Checkpoint preserved; rerun the same command to resume.")
        raise SystemExit(130) from None
    print(json.dumps(report, indent=2))
    if report["failed"] or report["pending"]:
        raise SystemExit("Some records unresolved; inspect ignored load-report.json and rerun")


if __name__ == "__main__":
    main()
