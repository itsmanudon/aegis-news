from datetime import timedelta
from typing import get_type_hints

import jsonschema
import pytest
from pydantic import ValidationError

from aegis.domain import models
from aegis.domain.ids import new_id
from aegis.intelligence import interfaces


@pytest.mark.parametrize(
    "port,method",
    [
        (interfaces.SentimentAnalyzer, "analyze"),
        (interfaces.TopicClassifier, "classify"),
        (interfaces.EntityExtractor, "extract"),
        (interfaces.EntityResolver, "resolve"),
        (interfaces.EventExtractor, "extract"),
        (interfaces.EmbeddingProvider, "embed"),
    ],
)
def test_model_ports_return_analysis(port, method):
    assert get_type_hints(getattr(port, method))["return"] is models.AnalysisResult


@pytest.fixture(
    params=["entity_extraction", "embedding", "event_extraction", "event_classification"]
)
def hardened_analysis(request, analysis, document):
    outputs = {
        "entity_extraction": dict(
            result_type="entity_extraction",
            surface="Example",
            start_offset=0,
            end_offset=7,
            predicted_kind="organization",
            confidence=0.9,
        ),
        "embedding": dict(result_type="embedding", values=[0.1, -0.2, 0.3]),
        "event_extraction": dict(
            result_type="event_extraction",
            proposed_event_type="notice",
            confidence=0.8,
            document_id=document.document_id,
            evidence_text="published a notice",
        ),
        "event_classification": dict(
            result_type="event_classification",
            event_id=new_id("evt"),
            event_revision=2,
            label="notice",
            confidence=0.8,
        ),
    }
    return models.AnalysisResult.model_validate(
        {
            **analysis.model_dump(),
            "analysis_type": request.param,
            "outputs": [outputs[request.param]],
        }
    )


def test_outputs_roundtrip_with_lineage_and_schema(hardened_analysis):
    value = hardened_analysis
    assert models.AnalysisResult.model_validate_json(value.model_dump_json()) == value
    jsonschema.validate(value.model_dump(mode="json"), models.AnalysisResult.model_json_schema())
    assert value.outputs[0].result_type == value.analysis_type
    with pytest.raises(ValidationError):
        value.model_version = "overwrite"
    with pytest.raises(ValidationError):
        value.outputs[0].result_type = "topic"
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate({**value.model_dump(), "trading_signal": "buy"})
    data = value.model_dump()
    data["outputs"][0]["trading_signal"] = "buy"
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate(data)


@pytest.mark.parametrize(
    "field",
    [
        "analysis_id",
        "provider",
        "model_name",
        "model_version",
        "configuration_hash",
        "created_at",
        "available_at",
    ],
)
def test_lineage_fields_required(hardened_analysis, field):
    data = hardened_analysis.model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate(data)


@pytest.mark.parametrize("field", ["provider", "model_name", "model_version", "configuration_hash"])
def test_model_metadata_cannot_be_empty(hardened_analysis, field):
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate({**hardened_analysis.model_dump(), field: ""})


def test_new_model_run_retains_old_analysis_and_actual_availability(hardened_analysis):
    old = hardened_analysis
    new = models.AnalysisResult.model_validate(
        {
            **old.model_dump(),
            "analysis_id": new_id("ana"),
            "model_version": "2",
            "configuration_hash": "1" * 64,
            "created_at": old.created_at + timedelta(hours=1),
            "available_at": old.available_at + timedelta(hours=2),
        }
    )
    assert old.model_version == "1"
    assert new.analysis_id != old.analysis_id
    assert new.available_at > old.available_at
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate(
            {
                **new.model_dump(),
                "available_at": old.created_at - timedelta(seconds=1),
            }
        )
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate({**old.model_dump(), "analysis_type": "topic"})


@pytest.mark.parametrize("revision", [None, 0, -1])
def test_event_classification_requires_exact_positive_revision(revision):
    data = dict(event_id=new_id("evt"), label="notice", confidence=0.8)
    if revision is not None:
        data["event_revision"] = revision
    with pytest.raises(ValidationError):
        models.EventClassificationResult.model_validate(data)


def test_fact_mentions_cannot_reference_analysis(document):
    data = dict(
        mention_id=new_id("mention"),
        document_id=document.document_id,
        surface="Example",
        start_offset=0,
        end_offset=7,
        evidence_kind="fact",
    )
    assert models.EntityMention.model_validate(data).analysis_id is None
    with pytest.raises(ValidationError):
        models.EntityMention.model_validate({**data, "analysis_id": new_id("ana")})


def test_document_media_link_is_explicit_and_frozen(document):
    link = models.DocumentMediaLink(document_id=document.document_id, media_id=new_id("media"))
    assert models.DocumentMediaLink.model_validate_json(link.model_dump_json()) == link
    with pytest.raises(ValidationError):
        link.media_id = new_id("media")
    with pytest.raises(ValidationError):
        models.DocumentMediaLink.model_validate(
            {**link.model_dump(), "ingestion_id": new_id("ing")}
        )


@pytest.mark.parametrize("values", [[], [float("nan")], [float("inf")], [float("-inf")]])
def test_embedding_rejects_empty_and_nonfinite_vectors(values):
    with pytest.raises(ValidationError):
        models.EmbeddingResult(values=values)


@pytest.mark.parametrize("start,end", [(-1, 7), (7, 7), (8, 7)])
def test_entity_extraction_rejects_invalid_spans(start, end):
    with pytest.raises(ValidationError):
        models.EntityExtractionResult(
            surface="Example", start_offset=start, end_offset=end, confidence=0.9
        )


def test_event_extraction_evidence_belongs_to_analyzed_document(analysis):
    output = models.EventExtractionResult(
        proposed_event_type="notice",
        confidence=0.8,
        document_id=new_id("doc"),
        evidence_text="published a notice",
    )
    with pytest.raises(ValidationError):
        models.AnalysisResult.model_validate(
            {
                **analysis.model_dump(),
                "analysis_type": "event_extraction",
                "outputs": [output],
            }
        )
