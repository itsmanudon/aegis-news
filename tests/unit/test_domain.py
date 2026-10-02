from datetime import timedelta

import pytest
from pydantic import ValidationError

from aegis.domain.ids import new_id
from aegis.domain.models import (
    AnalysisResult,
    AssetMapping,
    EntityMention,
    NewsDocument,
    NewsEvent,
    RawIngestion,
    Source,
)


def test_identifier_factory_and_validation(now):
    source = Source(source_id=new_id("src"), name="Synthetic", kind="upload", created_at=now)
    assert source.source_id.startswith("src_")
    with pytest.raises(ValidationError):
        Source(source_id=new_id("doc"), name="Synthetic", kind="upload", created_at=now)


def test_publisher_time_is_not_local_arrival_order(document, now):
    data = document.model_dump()
    data["published_at"] = now + timedelta(days=1)  # Publishers may report wrong/future clocks.
    assert NewsDocument.model_validate(data).published_at > document.first_seen_at
    data["published_at"] = None
    data["ingested_at"] = now - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        NewsDocument.model_validate(data)


def test_naive_time_and_speculative_fields_rejected(document):
    data = document.model_dump()
    data["first_seen_at"] = document.first_seen_at.replace(tzinfo=None)
    with pytest.raises(ValidationError):
        NewsDocument.model_validate(data)
    data = document.model_dump()
    data["buy_signal"] = True
    with pytest.raises(ValidationError):
        NewsDocument.model_validate(data)


def test_ingestion_timestamp_order(document, now):
    data = dict(
        ingestion_id=document.ingestion_id,
        source_id=document.source_id,
        raw_object_id=new_id("raw"),
        object=dict(
            bucket="synthetic",
            key="fixture",
            sha256="0" * 64,
            size_bytes=0,
            content_type="text/plain",
        ),
        first_seen_at=now,
        ingested_at=now,
        idempotency_key="fixture",
    )
    assert RawIngestion(**data).published_at is None
    data["ingested_at"] = now - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        RawIngestion(**data)


def test_analysis_is_immutable_and_nested_outputs_frozen(analysis):
    with pytest.raises(ValidationError):
        analysis.model_version = "2"
    with pytest.raises(ValidationError):
        analysis.outputs[0].label = "overwrite"
    new = analysis.model_dump()
    new["analysis_id"] = new_id("ana")
    new["model_version"] = "2"
    assert AnalysisResult.model_validate(new).analysis_id != analysis.analysis_id
    assert analysis.model_version == "1"


@pytest.mark.parametrize(
    "field,value",
    [("configuration_hash", "invalid"), ("outputs", []), ("analysis_type", "sentiment")],
)
def test_analysis_metadata_and_output_validation(analysis, field, value):
    data = analysis.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_analysis_available_time(analysis):
    data = analysis.model_dump()
    data["available_at"] = analysis.created_at - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_entity_asset_identity_is_separate(now):
    mapping = AssetMapping(
        mapping_id=new_id("map"),
        entity_id=new_id("ent"),
        scheme="exchange_symbol",
        identifier="AAPL",
        venue="NASDAQ",
        created_at=now,
    )
    assert mapping.entity_id != mapping.identifier
    with pytest.raises(ValidationError):
        AssetMapping.model_validate({**mapping.model_dump(), "venue": None})


def test_model_mentions_require_analysis_reference(document):
    data = dict(
        mention_id=new_id("mention"),
        document_id=document.document_id,
        surface="Example",
        start_offset=0,
        end_offset=7,
        evidence_kind="model_output",
    )
    with pytest.raises(ValidationError):
        EntityMention(**data)
    mention = EntityMention(**data, analysis_id=new_id("ana"))
    assert mention.entity_id is None
    with pytest.raises(ValidationError):
        EntityMention.model_validate({**mention.model_dump(), "end_offset": 0})


def test_event_requires_documents_and_declared_evidence(document, now):
    data = dict(
        event_id=new_id("evt"),
        summary="Synthetic notice",
        document_ids=(document.document_id,),
        evidence_kind="fact",
        created_at=now,
        available_at=now,
    )
    assert NewsEvent(**data).occurred_at is None
    with pytest.raises(ValidationError):
        NewsEvent.model_validate({**data, "evidence_kind": "model_output"})
