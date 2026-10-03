import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from aegis.domain.ids import new_id
from aegis.domain.models import AnalysisResult, ModelOutput, NewsDocument
from aegis.intelligence.config import ModelSpec
from aegis.intelligence.errors import NoPredictions, UnsupportedLanguage
from aegis.intelligence.taxonomy import EVENTS, NEGATIVE, POSITIVE, TOPICS

IMPLEMENTATION_VERSION = "aegis-local-1"


def configuration_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_document(document: NewsDocument) -> None:
    # Also rejects unvalidated model_copy updates at integration boundaries.
    NewsDocument.model_validate(document.model_dump())
    if document.language and document.language.split("-")[0].lower() != "en":
        raise UnsupportedLanguage("initial local models support English only")


def envelope(
    document: NewsDocument,
    spec: ModelSpec,
    outputs: tuple[ModelOutput, ...],
    started: datetime,
    runtime_metadata: dict[str, str],
    context: Any = None,
) -> AnalysisResult:
    if not outputs:
        raise NoPredictions("no predictions; no analysis persisted")
    return AnalysisResult(
        analysis_id=new_id("ana"),
        document_id=document.document_id,
        analysis_type=outputs[0].result_type,
        provider=f"local-{spec.backend}",
        model_name=spec.model_name,
        model_version=spec.revision,
        configuration_hash=configuration_hash(
            {
                "model": spec.model_dump(),
                "runtime": runtime_metadata,
                "implementation": IMPLEMENTATION_VERSION,
                "taxonomies": {"topics": TOPICS, "events": EVENTS},
                "lexicon": {"positive": POSITIVE, "negative": NEGATIVE},
                "context": context,
            }
        ),
        created_at=started,
        available_at=datetime.now(UTC),
        outputs=outputs,
    )
