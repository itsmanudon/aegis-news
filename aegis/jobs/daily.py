"""The daily news job: fetch, ingest, analyse and sign in one container, then exit.

    python -m aegis.jobs.daily

It starts a throwaway Temporal development server (the Temporal CLI, held in memory) and
the normal worker in this process, so every article runs through the same
NewsIngestionWorkflow as the long-running stack, with its retries. Articles reach
ingestion directly instead of through the API over HTTP. The job waits for every
workflow, prints a JSON report and exits 0 only when everything it asked for finished.

Nothing survives the Temporal server: Postgres and the object store hold all state, and
an article an interrupted run left unfinished is submitted again on the next run.
"""

import asyncio
import json
import logging
import shutil
import sys
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel
from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment

from aegis.domain.ids import new_id
from aegis.domain.models import Source
from aegis.ingestion.inputs import IngestionRequest, decode_content, decode_media
from aegis.ingestion.repository import IngestionRepository
from aegis.ingestion.runtime import make_service
from aegis.ingestion.submissions import TemporalSubmissions
from aegis.normalization.article import parse_article
from aegis.observability.logging import configure_logging
from aegis.persistence.database import make_engine, session_factory
from aegis.providers.models import FetchOptions, ProviderRun
from aegis.providers.persistence import ProviderStore
from aegis.providers.service import Acquisition, ProviderRunner
from aegis.security.keys import validate_key_id
from aegis.settings import Settings, get_settings
from apps.worker.main import build_worker

logger = logging.getLogger("aegis.jobs.daily")
# Provider outcomes that are not the job's fault: the day's budget is spent.
EXPECTED_SKIPS = frozenset({"daily_budget_reached"})


class JobReport(BaseModel):
    started_at: datetime
    finished_at: datetime
    run: ProviderRun
    completed: int = 0
    already_done: int = 0
    failed: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        providers_ok = all(
            outcome.status == "submitted" or outcome.error in EXPECTED_SKIPS
            for outcome in self.run.outcomes
        )
        return providers_ok and not self.failed


class DirectGateway:
    """The two ingestion routes the provider runner calls, without the HTTP hop."""

    def __init__(self, repository: IngestionRepository, submissions: TemporalSubmissions) -> None:
        self.repository, self.submissions = repository, submissions

    async def request(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        if (method, path) == ("POST", "/api/v1/sources"):
            source = Source(
                source_id=new_id("src"),
                name=body["name"],
                kind=body["kind"],
                url=body.get("url"),
                created_at=datetime.now(UTC),
            )
            created = await asyncio.to_thread(self.repository.create_source, source)
            return {"source_id": created.source_id}
        if (method, path) == ("POST", "/api/v1/ingestions"):
            request = IngestionRequest.model_validate(body)
            # The same checks the API route makes before it starts a workflow.
            parse_article(decode_content(request), request.content_type)
            for media in request.media:
                decode_media(media)
            return await self.submissions.submit(request)
        raise ValueError(f"unsupported gateway call {method} {path}")


@contextmanager
def signing_keys(settings: Settings) -> Iterator[Settings]:
    """Settings whose key directory holds the signing key from the environment, if given."""
    pem = settings.provenance_signing_key.get_secret_value()
    if not pem:
        yield settings
        return
    validate_key_id(settings.provenance_key_id)
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("AEGIS_PROVENANCE_SIGNING_KEY must be an Ed25519 private key")
    with tempfile.TemporaryDirectory(prefix="aegis-keys-") as directory:
        folder = Path(directory)
        folder.chmod(0o700)
        public = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        for suffix, value in (("ed25519.key", pem.encode()), ("ed25519.pub", public)):
            path = folder / f"{settings.provenance_key_id}.{suffix}"
            path.touch(mode=0o600)
            path.write_bytes(value)
        yield settings.model_copy(update={"security_key_directory": folder})


def temporal_cli(settings: Settings) -> str:
    found = shutil.which(settings.temporal_cli_path)
    if not found:
        # Never download a server at run time: the image must carry a pinned CLI.
        raise FileNotFoundError(f"Temporal CLI not found: {settings.temporal_cli_path}")
    return found


async def wait_for(
    client: Client, store: ProviderStore, run: ProviderRun, timeout: float
) -> tuple[int, int, tuple[str, ...]]:
    """Wait for every workflow of the run. Returns (completed, already done, failed)."""
    completed = already = 0
    failed: list[str] = []
    workflow_ids = sorted({w for outcome in run.outcomes for w in outcome.workflow_ids})

    async def one(workflow_id: str) -> None:
        nonlocal completed, already
        try:
            result = await client.get_workflow_handle(workflow_id).result()
        except RPCError as exc:
            # Submitted by an earlier run that finished; this server never saw it.
            done = await asyncio.to_thread(store.document_for_workflow, workflow_id)
            if exc.status == RPCStatusCode.NOT_FOUND and done is not None:
                already += 1
                return
            failed.append(workflow_id)
            return
        except Exception:
            failed.append(workflow_id)
            return
        await asyncio.to_thread(store.completed, workflow_id, result["document_id"])
        completed += 1

    try:
        async with asyncio.timeout(timeout):
            await asyncio.gather(*(one(w) for w in workflow_ids))
    except TimeoutError:
        logger.error("daily_job_timeout")
        done = set(failed)
        failed.extend(w for w in workflow_ids if w not in done)
    return completed, already, tuple(sorted(set(failed)))


async def run(settings: Settings, adapters: Mapping[str, Acquisition] | None = None) -> JobReport:
    started = datetime.now(UTC)
    settings = settings.model_copy(update={"provenance_archive_enabled": False})
    with signing_keys(settings) as settings:
        environment = await WorkflowEnvironment.start_local(
            namespace=settings.temporal_namespace,
            dev_server_existing_path=temporal_cli(settings),
            dev_server_log_level="error",
            ui=False,
        )
        service = make_service(settings)
        engine = make_engine(settings)
        try:
            store = ProviderStore(session_factory(engine))
            submissions = TemporalSubmissions(settings)
            submissions.client = environment.client
            async with build_worker(environment.client, settings, service):
                report = await ProviderRunner(settings, store, resubmit_unfinished=True).execute(
                    list(settings.job_providers),
                    FetchOptions(
                        query=settings.job_query,
                        limit=settings.job_limit,
                        country=settings.job_country,
                    ),
                    DirectGateway(service.repository, submissions),
                    adapters,
                )
                completed, already, failed = await wait_for(
                    environment.client, store, report, settings.job_timeout_seconds
                )
        finally:
            service.repository.close()
            engine.dispose()
            await environment.shutdown()
    return JobReport(
        started_at=started,
        finished_at=datetime.now(UTC),
        run=report,
        completed=completed,
        already_done=already,
        failed=failed,
    )


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_file)
    try:
        report = asyncio.run(run(settings))
    except Exception as exc:
        # The type only: messages from HTTP and key handling may carry secrets.
        print(json.dumps({"ok": False, "error": type(exc).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": report.ok, **report.model_dump(mode="json")}, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
