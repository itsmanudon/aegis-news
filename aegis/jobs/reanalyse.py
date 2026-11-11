"""Analyse and sign documents again, for example after a model was missing or replaced.

    python -m aegis.jobs.reanalyse DOCUMENT_ID [DOCUMENT_ID ...]

Each document gets a new run: all six analyses again with the current profile, then a new
signed manifest. Its feed bundle moves forward, so consumers receive the new analyses on
their next sync. Runs in-process with the daily job's settings and key handling; Temporal
is not needed. Prints a JSON report and exits 0 only if every document was re-signed.
"""

import argparse
import asyncio
import json
import sys
from uuid import uuid4

from aegis.ingestion.runtime import make_service
from aegis.intelligence.engine import build_engine
from aegis.intelligence.pipeline import AnalysisPipeline
from aegis.jobs.daily import signing_keys
from aegis.provenance.service import ProvenanceService
from aegis.security.crypto import StandardCryptoProvider
from aegis.security.keys import FileKeyProvider
from aegis.settings import Settings, get_settings
from apps.worker.intelligence_activities import IntelligenceActivities

TASKS = ("entities", "topics", "sentiment", "embedding", "resolution", "events")


async def reanalyse(settings: Settings, document_ids: list[str]) -> dict[str, str]:
    settings = settings.model_copy(update={"provenance_archive_enabled": False, "ai_strict": True})
    outcome: dict[str, str] = {}
    with signing_keys(settings) as settings:
        service = make_service(settings)
        try:
            worker = IntelligenceActivities(
                service,
                build_engine(settings.ai_profile),
                AnalysisPipeline(
                    service.repository,
                    ProvenanceService(
                        StandardCryptoProvider(FileKeyProvider(settings.security_key_directory))
                    ),
                    settings.provenance_key_id,
                ),
                archive=False,
                strict=True,
            )
            for document_id in document_ids:
                run_key = "reanalyse-" + uuid4().hex
                try:
                    await asyncio.to_thread(service.repository.get_document, document_id)
                    ids = []
                    for task in TASKS:
                        result = await worker.analyze(task, document_id, run_key, "reanalyse")
                        if "analysis_id" in result:
                            ids.append(result["analysis_id"])
                    await worker.provenance(document_id, run_key, ids)
                    outcome[document_id] = "signed"
                except LookupError:
                    outcome[document_id] = "not_found"
                except Exception as exc:  # noqa: BLE001 - reported per document, then the next
                    # A strict-mode failure carries the model error's name in ``type``.
                    outcome[document_id] = "failed: " + (
                        getattr(exc, "type", None) or type(exc).__name__
                    )
        finally:
            service.repository.close()
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("document_ids", nargs="+")
    args = parser.parse_args(argv)
    outcome = asyncio.run(reanalyse(get_settings(), args.document_ids))
    print(json.dumps(outcome, indent=2))
    return 0 if all(value == "signed" for value in outcome.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
