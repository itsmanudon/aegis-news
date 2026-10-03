"""Opt-in real Temporal comparison using an isolated stack and a local CPU worker."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client

from aegis.ingestion.runtime import make_service
from aegis.persistence.models import AnalysisRow
from aegis.settings import Settings
from scripts.demo_seed import seed


def validate_local_target(settings: Settings, url: str) -> None:
    if settings.environment != "development" or not settings.dev_identity_enabled:
        raise ValueError("benchmark requires explicit local development identity")
    endpoints = [
        url,
        settings.database_url.get_secret_value(),
        settings.redis_url.get_secret_value(),
        settings.s3_endpoint_url,
        "//" + settings.temporal_address,
    ]
    if any(urlsplit(value).hostname not in {"localhost", "127.0.0.1"} for value in endpoints):
        raise ValueError("benchmark endpoints must all be local")


async def wait_worker(
    client: Client, worker: subprocess.Popen[bytes], settings: Settings, identity: str
) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if worker.poll() is not None:
            raise RuntimeError("benchmark worker exited; inspect ignored worker log")
        response = await client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(
                namespace=settings.temporal_namespace,
                task_queue=TaskQueue(name=settings.temporal_task_queue),
                task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
            )
        )
        if any(p.identity == identity for p in response.pollers):
            return
        await asyncio.sleep(0.2)
    raise TimeoutError("benchmark worker did not poll the isolated Temporal task queue")


async def run(profile: str, url: str, rounds: int, log: Path) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("positive warm rounds required")
    settings = Settings()
    validate_local_target(settings, url)
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    identity = "evaluation-" + uuid4().hex
    environment = {
        **os.environ,
        "AEGIS_AI_PROFILE": profile,
        "HF_HUB_OFFLINE": "1",
        "AEGIS_BENCHMARK_IDENTITY": identity,
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    batches = []
    with log.open("wb") as output:
        # Explicit SDK identity avoids stale pollers and Windows venv launcher child PIDs.
        # Only benchmark instrumentation changes; the existing worker entrypoint runs as-is.
        entrypoint = """import asyncio, os
from temporalio.client import Client
from apps.worker.main import main
connect = Client.connect
async def identified_connect(*args, **kwargs):
    kwargs['identity'] = os.environ['AEGIS_BENCHMARK_IDENTITY']
    return await connect(*args, **kwargs)
Client.connect = identified_connect
asyncio.run(main())
"""
        worker = subprocess.Popen(
            [sys.executable, "-c", entrypoint],
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            await wait_worker(client, worker, settings, identity)
            # Each batch has distinct ingestion keys. Historical/demo data is never deleted.
            for index in range(rounds + 1):
                report = await seed(url, f"eval-{profile}-{uuid4().hex}")
                if report["fresh_document_count"] != 5:
                    raise RuntimeError("cached processing is not a valid fresh pipeline benchmark")
                report["temperature"] = "cold worker/model cache" if index == 0 else "warm models"
                service = make_service(settings)
                try:
                    ids = [doc["document_id"] for doc in report["documents"]]
                    with service.repository.sessions() as session:
                        analyses = session.scalars(
                            select(AnalysisRow).where(AnalysisRow.document_id.in_(ids))
                        ).all()
                        report["persisted_models"] = sorted(
                            {f"{row.model_name}@{row.model_version}" for row in analyses}
                        )
                        report["analyses_in_batch"] = len(analyses)
                finally:
                    service.repository.close()
                batches.append(report)
        finally:
            worker.terminate()
            await asyncio.to_thread(worker.wait, 10)
    return {
        "profile": profile,
        "result": "passed",
        "device": "cpu, unchanged existing profile",
        "topology": "Docker API/PostgreSQL/Redis/MinIO/Temporal; local optional Python worker",
        "batches": batches,
        "protocol": (
            "Identical five CC0 demo items/media per batch; fresh ingestion keys; one model-cold "
            "batch followed by warm batches; complete existing NewsIngestionWorkflow including "
            "raw storage, SQL persistence, AI, provenance/sign/encrypted archive and verification; "
            "duplicate retry verified; cold excludes download/install and worker registration; "
            "host/container workload uncontrolled; not production-scale performance"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("offline", "light"), required=True)
    parser.add_argument("--api-url", default="http://localhost:38000")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(
        run(
            args.profile, args.api_url, args.rounds, Path(".evaluation-tmp") / f"{args.profile}.log"
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
