import os
from datetime import UTC, datetime

import pytest

from aegis.domain.ids import new_id
from aegis.domain.models import AnalysisResult, NewsDocument, TopicResult


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker, flag in (("integration", "AEGIS_RUN_INTEGRATION"), ("e2e", "AEGIS_RUN_E2E")):
            if marker in item.keywords and os.environ.get(flag) != "1":
                item.add_marker(
                    pytest.mark.skip(reason=f"Set {flag}=1 with local services running")
                )


@pytest.fixture
def now():
    return datetime.now(UTC)


@pytest.fixture
def document(now):
    return NewsDocument(
        document_id=new_id("doc"),
        ingestion_id=new_id("ing"),
        source_id=new_id("src"),
        title="Synthetic foundation fixture",
        text="Example organization published a notice.",
        first_seen_at=now,
        ingested_at=now,
        created_at=now,
    )


@pytest.fixture
def analysis(document, now):
    return AnalysisResult(
        analysis_id=new_id("ana"),
        document_id=document.document_id,
        analysis_type="topic",
        provider="synthetic",
        model_name="fixture",
        model_version="1",
        configuration_hash="0" * 64,
        created_at=now,
        available_at=now,
        outputs=(TopicResult(label="notice", confidence=0.9),),
    )
