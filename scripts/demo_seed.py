"""Idempotent synthetic demo seed and real Temporal-history latency measurements."""

import argparse
import asyncio
import base64
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from temporalio.client import Client

from aegis.domain.models import Entity
from aegis.ingestion.runtime import make_service
from aegis.intelligence.assessment import latency_report
from aegis.intelligence.pipeline import stable_id
from aegis.persistence.models import AnalysisRow, DocumentRow, EntityRow, OutboxRow
from aegis.security.dev_identity import issue_development_token
from aegis.security.keys import FileKeyProvider
from aegis.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


class DemoClient:
    def __init__(self, url: str = "http://api:8000") -> None:
        self.settings = Settings()
        if self.settings.environment != "development" or not self.settings.dev_identity_enabled:
            raise ValueError("Demo writes are restricted to explicit local development")
        self.keys = FileKeyProvider(self.settings.security_key_directory)
        self.url = url

    def request(self, path: str, body: Any = None, role: str | None = "admin") -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if role:
            token = issue_development_token(
                self.settings, self.keys, key_id="local", subject="phase6-demo", role=role
            )
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            value: dict[str, Any] = json.load(response)
            return value

    async def wait(self, workflow_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            run = await asyncio.to_thread(self.request, "/api/v1/ingestion-runs/" + workflow_id)
            state = run["data"]
            if state["status"] == "COMPLETED":
                return dict(state["result"])
            if state["status"] in {"FAILED", "TIMED_OUT", "TERMINATED", "CANCELED"}:
                raise RuntimeError("Demo workflow did not complete successfully")
            await asyncio.sleep(0.5)
        raise TimeoutError("Demo workflow timeout")


def counts(service: Any, source_id: str) -> dict[str, int]:
    with service.repository.sessions() as session:
        docs = select(DocumentRow.document_id).where(DocumentRow.source_id == source_id)
        return {
            "documents": int(
                session.scalar(
                    select(func.count())
                    .select_from(DocumentRow)
                    .where(DocumentRow.source_id == source_id)
                )
                or 0
            ),
            "analyses": int(
                session.scalar(
                    select(func.count())
                    .select_from(AnalysisRow)
                    .where(AnalysisRow.document_id.in_(docs))
                )
                or 0
            ),
            "outbox_total": int(session.scalar(select(func.count()).select_from(OutboxRow)) or 0),
        }


async def timings(client: Client, identity: str) -> dict[str, Any]:
    history = await client.get_workflow_handle(identity).fetch_history()
    scheduled: dict[int, str] = {}
    started: dict[int, datetime] = {}
    durations: dict[str, list[float]] = {}
    for event in history.events:
        if event.HasField("activity_task_scheduled_event_attributes"):
            scheduled[event.event_id] = (
                event.activity_task_scheduled_event_attributes.activity_type.name
            )
        elif event.HasField("activity_task_started_event_attributes"):
            started[event.event_id] = event.event_time.ToDatetime(tzinfo=UTC)
        elif event.HasField("activity_task_completed_event_attributes"):
            attributes = event.activity_task_completed_event_attributes
            duration = (
                event.event_time.ToDatetime(tzinfo=UTC) - started[attributes.started_event_id]
            ).total_seconds() * 1000
            durations.setdefault(scheduled[attributes.scheduled_event_id], []).append(duration)
    elapsed = (
        history.events[-1].event_time.ToDatetime(tzinfo=UTC)
        - history.events[0].event_time.ToDatetime(tzinfo=UTC)
    ).total_seconds() * 1000
    return {"workflow_id": identity, "total_ms": elapsed, "activity_ms": durations}


async def seed(url: str, mode: str, run_key: str = "v1") -> dict[str, Any]:
    api = DemoClient(url)
    service = make_service(api.settings)
    try:
        sources = api.request("/api/v1/sources?limit=100")["data"]
        source = next((s for s in sources if s["name"] == "CC0 presentation demo v1"), None)
        if source is None:
            source = api.request(
                "/api/v1/sources", {"name": "CC0 presentation demo v1", "kind": "upload"}
            )["data"]
        samples = json.loads((ROOT / "data/samples/mvp.json").read_text(encoding="utf-8"))
        with service.repository.sessions.begin() as session:
            for sample in samples:
                identity = stable_id("ent", "demo:" + sample["entity"])
                if session.get(EntityRow, identity) is None:
                    entity = Entity(
                        entity_id=identity,
                        canonical_name=sample["entity"],
                        kind=sample["kind"],
                        created_at=datetime.now(UTC),
                    )
                    session.add(EntityRow(**entity.model_dump()))
        items = []
        for i, sample in enumerate(samples):
            article = {key: sample[key] for key in ("title", "text", "published_at")}
            article["language"] = "en"
            item: dict[str, Any] = {
                "source_id": source["source_id"],
                "idempotency_key": f"{mode}-{i}-v1",
                "content_type": "application/json",
                "content_base64": base64.b64encode(json.dumps(article).encode()).decode(),
                "correlation_id": "aegis-demo-v1",
            }
            if sample.get("media") or i == 0:
                item["media"] = [
                    {
                        "kind": "image",
                        "content_type": "image/png",
                        "content_base64": base64.b64encode(
                            (ROOT / "data/samples/demo-image.png").read_bytes()
                        ).decode(),
                    }
                ]
            items.append(item)
        if mode.startswith("recovery"):
            item = {**items[0], "idempotency_key": "recovery-" + run_key}
            workflow_id = api.request("/api/v1/ingestions", item)["data"]["workflow_id"]
            if mode == "recovery-submit":
                state = api.request("/api/v1/ingestion-runs/" + workflow_id)["data"]
                assert state["status"] == "RUNNING"
                return {
                    "workflow_id": workflow_id,
                    "worker_stopped": True,
                    "status": state["status"],
                }
            result = await api.wait(workflow_id)
            assert api.request(f"/api/v1/documents/{result['document_id']}/verify", {})["data"][
                "valid"
            ]
            return {
                "result": "passed",
                "workflow_id": workflow_id,
                "document_id": result["document_id"],
                "resumed_after_worker_restart": True,
                "verification": "valid",
            }
        started = time.perf_counter()
        previous_counts = counts(service, source["source_id"])
        submissions = api.request("/api/v1/ingestions/batch", {"items": items})["data"][
            "submissions"
        ]
        results = await asyncio.gather(*(api.wait(s["workflow_id"]) for s in submissions))
        before = counts(service, source["source_id"])
        duplicate = api.request("/api/v1/ingestions/batch", {"items": items})["data"]["submissions"]
        assert [s["workflow_id"] for s in submissions] == [s["workflow_id"] for s in duplicate]
        assert before == counts(service, source["source_id"])
        for result in results:
            assert api.request(f"/api/v1/documents/{result['document_id']}/verify", {}, "analyst")[
                "data"
            ]["valid"]
        temporal = await Client.connect(api.settings.temporal_address)
        histories = [await timings(temporal, s["workflow_id"]) for s in submissions]
        stages: dict[str, list[float]] = {}
        for history in histories:
            for stage, values in history["activity_ms"].items():
                stages.setdefault(stage, []).extend(values)
        wall = time.perf_counter() - started
        return {
            "result": "passed",
            "mode": mode,
            "source_id": source["source_id"],
            "documents": results,
            "workflow_ids": [s["workflow_id"] for s in submissions],
            "counts_after": before,
            "duplicate_stable": True,
            "media_document_id": results[0]["document_id"],
            "batch_wall_seconds_including_verification": wall,
            "fresh_document_count": before["documents"] - previous_counts["documents"],
            "batch_throughput_documents_per_second": len(results) / wall
            if before["documents"] - previous_counts["documents"] == len(results)
            else None,
            "history_latency": {k: latency_report(v) for k, v in stages.items()},
            "total_pipeline": latency_report([h["total_ms"] for h in histories]),
            "protocol": (
                "Five concurrent short synthetic items on local Docker; activity server "
                "timestamps include I/O; no scale or pure inference claim; "
                "rerun after reset for fresh-work timing"
            ),
        }
    finally:
        service.repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://api:8000")
    parser.add_argument("--run-key", default="v1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--benchmark", action="store_true")
    mode.add_argument("--recovery-submit", action="store_true")
    mode.add_argument("--recovery-wait", action="store_true")
    args = parser.parse_args()
    selected = (
        "benchmark"
        if args.benchmark
        else "recovery-submit"
        if args.recovery_submit
        else "recovery-wait"
        if args.recovery_wait
        else "seed"
    )
    print(json.dumps(asyncio.run(seed(args.api_url, selected, args.run_key)), indent=2))


if __name__ == "__main__":
    main()
