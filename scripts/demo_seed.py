"""Idempotent synthetic demo seed and real Temporal-history latency measurements."""

import argparse
import asyncio
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import jwt
from sqlalchemy import func, select, text
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
SHOWCASE_SOURCE = "CC0 showcase demo v1"
PRESENTATION_SOURCE = "CC0 presentation demo v1"
BATCH_SIZE = 5


class DemoClient:
    def __init__(self, url: str = "http://api:8000") -> None:
        self.settings = Settings()
        if self.settings.environment != "development" or not self.settings.dev_identity_enabled:
            raise ValueError("Demo writes are restricted to explicit local development")
        self.keys = FileKeyProvider(self.settings.security_key_directory)
        self.url = url

    def token(self, role: str, *, expired: bool = False) -> str:
        if not expired:
            return issue_development_token(
                self.settings, self.keys, key_id="local", subject="phase6-demo", role=role
            )
        now = datetime.now(UTC) - timedelta(minutes=10)
        return jwt.encode(
            {
                "iss": self.settings.oidc_issuer,
                "aud": self.settings.oidc_audience,
                "sub": "phase6-demo-expired",
                "iat": now,
                "exp": now + timedelta(minutes=1),
                "roles": [role],
                "scope": "documents:read",
            },
            self.keys.signing_key("local"),
            algorithm="EdDSA",
            headers={"kid": "local", "typ": "at+jwt"},
        )

    def status(
        self, path: str, body: Any = None, role: str | None = "admin", *, expired: bool = False
    ) -> tuple[int, dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if role:
            headers["Authorization"] = "Bearer " + self.token(role, expired=expired)
        request = urllib.request.Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method="POST" if body is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value: dict[str, Any] = json.load(response)
                return response.status, value
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {}
            if not isinstance(parsed, dict):
                parsed = {}
            return exc.code, parsed

    def request(self, path: str, body: Any = None, role: str | None = "admin") -> dict[str, Any]:
        status, value = self.status(path, body, role)
        if status >= 400:
            raise RuntimeError(f"Demo API {path} returned {status}")
        return value

    async def wait(self, workflow_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            run = await asyncio.to_thread(self.request, "/api/v1/ingestion-runs/" + workflow_id)
            state = run["data"]
            if state["status"] == "COMPLETED":
                return dict(state["result"])
            if state["status"] in {"FAILED", "TIMED_OUT", "TERMINATED", "CANCELED"}:
                raise RuntimeError(f"Demo workflow {workflow_id} ended {state['status']}")
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


def load_samples(name: str) -> list[dict[str, Any]]:
    payload = json.loads((ROOT / "data/samples" / name).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Sample file must be a list")
    return payload


def ensure_source(api: DemoClient, name: str) -> dict[str, Any]:
    sources = api.request("/api/v1/sources?limit=100")["data"]
    source = next((item for item in sources if item["name"] == name), None)
    if source is None:
        source = api.request("/api/v1/sources", {"name": name, "kind": "upload"})["data"]
    return cast(dict[str, Any], source)


def ensure_entities(service: Any, samples: list[dict[str, Any]]) -> None:
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


def article_items(
    samples: list[dict[str, Any]], source_id: str, prefix: str, correlation: str
) -> list[dict[str, Any]]:
    items = []
    for index, sample in enumerate(samples):
        # Key order matches the original five-item seed so existing fingerprints stay stable.
        article: dict[str, Any] = {"title": sample["title"], "text": sample["text"]}
        if sample.get("published_at"):
            article["published_at"] = sample["published_at"]
        article["language"] = "en"
        item: dict[str, Any] = {
            "source_id": source_id,
            "idempotency_key": f"{prefix}-{index}-v1",
            "content_type": "application/json",
            "content_base64": base64.b64encode(json.dumps(article).encode()).decode(),
            "correlation_id": correlation,
        }
        if sample.get("media") or (prefix == "seed" and index == 0):
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
    return items


async def ingest(
    api: DemoClient, items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    submissions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for offset in range(0, len(items), BATCH_SIZE):
        batch = items[offset : offset + BATCH_SIZE]
        accepted = api.request("/api/v1/ingestions/batch", {"items": batch})["data"]["submissions"]
        completed = await asyncio.gather(*(api.wait(item["workflow_id"]) for item in accepted))
        duplicate = api.request("/api/v1/ingestions/batch", {"items": batch})["data"]["submissions"]
        accepted_ids = [item["workflow_id"] for item in accepted]
        duplicate_ids = [item["workflow_id"] for item in duplicate]
        if accepted_ids != duplicate_ids:
            raise RuntimeError("Duplicate ingestion did not reuse workflow IDs")
        submissions.extend(accepted)
        results.extend(completed)
    return submissions, results


def scope_probe(api: DemoClient) -> dict[str, int]:
    unauthenticated, _ = api.status("/api/v1/documents?limit=1", role=None)
    expired, _ = api.status("/api/v1/documents?limit=1", role="analyst", expired=True)
    viewer_read, _ = api.status("/api/v1/documents?limit=1", role="viewer")
    viewer_write, _ = api.status(
        "/api/v1/sources", {"name": "viewer-must-not-create", "kind": "upload"}, "viewer"
    )
    analyst_verify_denied, _ = api.status(
        "/api/v1/sources",
        {"name": "analyst-must-not-create", "kind": "upload"},
        "analyst",
    )
    analyst_identity, identity = api.status("/api/v1/security/me", role="analyst")
    return {
        "unauthenticated": unauthenticated,
        "expired": expired,
        "viewer_read": viewer_read,
        "viewer_source_write": viewer_write,
        "analyst_source_write": analyst_verify_denied,
        "analyst_identity": analyst_identity,
        "analyst_subject_ok": int(identity.get("data", {}).get("subject") == "phase6-demo"),
    }


async def verify_intelligence(api: DemoClient, service: Any) -> dict[str, Any]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from apps.api.dependencies import ReadinessProbe

    head = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()
    with service.repository.sessions() as session:
        current = session.scalar(text("SELECT version_num FROM alembic_version"))
        analysis_rows = session.execute(
            text("SELECT analysis_type, COUNT(*) FROM analyses GROUP BY analysis_type")
        ).all()
    probe = ReadinessProbe(api.settings)
    try:
        dependencies = [{"name": item.name, "ready": item.ready} for item in await probe.check()]
    finally:
        await probe.close()
    topics_status, topics = api.status("/api/v1/topics?limit=50", role="analyst")
    topic_rows = topics.get("data") or []
    membership: dict[str, Any] = {}
    if topic_rows:
        topic = topic_rows[0]
        member_status, members = api.status(
            "/api/v1/topics/" + topic["topic_id"] + "/documents?limit=20", role="analyst"
        )
        membership = {
            "status": member_status,
            "topic_id": topic["topic_id"],
            "label": topic["label"],
            "document_count": topic["document_count"],
            "members": len(members.get("data") or []),
        }
    analytics_status, analytics = api.status(
        "/api/v1/analytics?start=2020-01-01T00:00:00Z&end=2021-01-01T00:00:00Z&time_basis=published_at",
        role="analyst",
    )
    report = analytics.get("data") or {}
    discovery_status, first = api.status(
        "/api/v1/discovery?limit=20&order=published_at", role="analyst"
    )
    cursor = (first.get("pagination") or {}).get("next_cursor")
    second: dict[str, Any] = {"data": []}
    second_status = None
    if cursor:
        second_status, second = api.status(
            "/api/v1/discovery?limit=20&order=published_at&cursor="
            + urllib.parse.quote(cursor, safe=""),
            role="analyst",
        )
    first_ids = [item["document"]["document_id"] for item in first.get("data") or []]
    second_ids = [item["document"]["document_id"] for item in second.get("data") or []]
    published = [
        item["document"]["published_at"]
        for item in (first.get("data") or [])
        if item["document"].get("published_at")
    ]
    documents_status, documents = api.status("/api/v1/documents?limit=5", role="analyst")
    document_id = (documents.get("data") or [{}])[0].get("document_id")
    verify_status, verified = api.status(f"/api/v1/documents/{document_id}/verify", {}, "analyst")
    historical_status, historical = api.status(
        "/api/v1/topics?limit=5&as_of=2019-01-01T00:00:00Z", role="analyst"
    )
    scopes = scope_probe(api)
    population = int(report.get("population_count") or 0)
    classified = int(report.get("classified_count") or 0)
    passed = (
        current == head
        and all(item["ready"] for item in dependencies)
        and topics_status == 200
        and bool(topic_rows)
        and membership.get("status") == 200
        and int(membership.get("members") or 0) > 0
        and int(membership.get("document_count") or 0) >= int(membership.get("members") or 0)
        and analytics_status == 200
        and population >= 1
        and classified <= population
        and discovery_status == 200
        and bool(first_ids)
        and published == sorted(published, reverse=True)
        and not (set(first_ids) & set(second_ids))
        and documents_status == 200
        and verify_status == 200
        and (verified.get("data") or {}).get("valid") is True
        and historical_status == 200
        and historical.get("data") == []
        and scopes["unauthenticated"] == 401
        and scopes["expired"] == 401
        and scopes["viewer_read"] == 200
        and scopes["viewer_source_write"] == 403
        and scopes["analyst_source_write"] == 403
        and scopes["analyst_identity"] == 200
        and scopes["analyst_subject_ok"] == 1
    )
    return {
        "result": "passed" if passed else "failed",
        "migration": current,
        "migration_head": head,
        "dependencies": dependencies,
        "topic_count": len(topic_rows),
        "membership": membership,
        "analytics": {
            "status": analytics_status,
            "population_count": population,
            "classified_count": classified,
            "unknown_time_count": report.get("unknown_time_count"),
            "start": report.get("start"),
            "end": report.get("end"),
        },
        "discovery": {
            "status": discovery_status,
            "first_page": len(first_ids),
            "second_page": len(second_ids),
            "second_status": second_status,
            "ordered": published == sorted(published, reverse=True),
            "pages_disjoint": not (set(first_ids) & set(second_ids)),
        },
        "verification": {
            "status": verify_status,
            "valid": (verified.get("data") or {}).get("valid"),
            "document_id": document_id,
        },
        "historical_cutoff_empty": historical.get("data") == [],
        "analysis_counts": {row[0]: int(row[1]) for row in analysis_rows},
        "scopes": scopes,
        "synthetic_disclosure": "Original synthetic demonstration records, not current news.",
    }


async def seed(
    url: str, mode: str, run_key: str = "v1", *, showcase: bool = False, verify_only: bool = False
) -> dict[str, Any]:
    api = DemoClient(url)
    service = make_service(api.settings)
    try:
        if verify_only:
            receipt = await verify_intelligence(api, service)
            return receipt
        source = ensure_source(api, PRESENTATION_SOURCE)
        samples = load_samples("mvp.json")
        ensure_entities(service, samples)
        items = article_items(samples, source["source_id"], mode, "aegis-demo-v1")
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
        payload: dict[str, Any] = {
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
            "showcase_documents": 0,
        }
        if mode == "seed" and showcase:
            extra = load_samples("showcase.json")
            showcase_source = ensure_source(api, SHOWCASE_SOURCE)
            ensure_entities(service, extra)
            showcase_items = article_items(
                extra, showcase_source["source_id"], "showcase", "aegis-demo-showcase-v1"
            )
            before_showcase = counts(service, showcase_source["source_id"])
            _accepted, showcase_results = await ingest(api, showcase_items)
            after_showcase = counts(service, showcase_source["source_id"])
            if after_showcase["documents"] < len(extra):
                raise RuntimeError("Showcase did not retain the expected documents")
            payload["showcase_documents"] = after_showcase["documents"]
            payload["showcase_fresh"] = after_showcase["documents"] - before_showcase["documents"]
            payload["showcase_verified"] = len(showcase_results)
            payload["showcase_source_id"] = showcase_source["source_id"]
        if mode == "seed":
            payload["intelligence"] = await verify_intelligence(api, service)
            if payload["intelligence"]["result"] != "passed":
                payload["result"] = "failed"
        return payload
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
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--showcase", action="store_true")
    args = parser.parse_args()
    selected = (
        "benchmark"
        if args.benchmark
        else "recovery-submit"
        if args.recovery_submit
        else "recovery-wait"
        if args.recovery_wait
        else "verify"
        if args.verify
        else "seed"
    )
    print(
        json.dumps(
            asyncio.run(
                seed(
                    args.api_url,
                    selected,
                    args.run_key,
                    showcase=args.showcase,
                    verify_only=args.verify,
                )
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
