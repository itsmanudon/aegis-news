import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import TypeAdapter, ValidationError

from aegis.contracts.api import (
    ApiErrorEnvelope,
    CollectionResponse,
    CursorPagination,
    ErrorCode,
    ErrorDetail,
    ResponseMeta,
)
from aegis.contracts.events import EVENT_MODELS, AsyncEvent
from aegis.domain.ids import new_id
from scripts.export_schemas import generated_schemas

ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_schemas_match_source():
    for path, value in generated_schemas().items():
        assert (ROOT / path).read_text() == value, f"Run schema export: {path}"
        if "openapi" not in str(path):
            jsonschema.Draft202012Validator.check_schema(json.loads(value))


@pytest.mark.parametrize("model", EVENT_MODELS)
def test_all_event_types_roundtrip_and_match_json_schema(model, document, now):
    event_type = model.model_fields["event_type"].default
    if event_type == "document.ingested.v1":
        data = dict(document_id=document.document_id, ingestion_id=document.ingestion_id)
    elif event_type == "document.normalized.v1":
        data = dict(document_id=document.document_id, revision=1)
    elif event_type == "analysis.completed.v1":
        data = dict(analysis_id=new_id("ana"), document_id=document.document_id, available_at=now)
    elif event_type == "entity.resolved.v1":
        data = dict(
            entity_id=new_id("ent"), mention_id=new_id("mention"), analysis_id=new_id("ana")
        )
    elif event_type.startswith("news.event."):
        data = dict(event_id=new_id("evt"), revision=1, available_at=now)
    else:
        data = dict(subject_id=document.document_id, reason_code="HASH_MISMATCH")
    value = model(
        event_id=new_id("msg"),
        occurred_at=now,
        producer="foundation-test",
        correlation_id="test",
        idempotency_key="synthetic",
        data=data,
    )
    encoded = value.model_dump(mode="json")
    assert TypeAdapter(AsyncEvent).validate_json(value.model_dump_json()) == value
    jsonschema.validate(
        encoded, json.loads((ROOT / f"schemas/events/{event_type}.json").read_text())
    )
    encoded["event_version"] = "2"
    with pytest.raises(ValidationError):
        TypeAdapter(AsyncEvent).validate_python(encoded)
    encoded["event_version"] = "1"
    encoded["data"]["unexpected"] = "value"
    with pytest.raises(ValidationError):
        TypeAdapter(AsyncEvent).validate_python(encoded)


@pytest.mark.parametrize("code", list(ErrorCode))
def test_error_contract(code):
    value = ApiErrorEnvelope(error=ErrorDetail(code=code, message="Synthetic", request_id="req"))
    jsonschema.validate(value.model_dump(mode="json"), ApiErrorEnvelope.model_json_schema())


def test_cursor_contract(document):
    value = CollectionResponse(
        data=(document,), pagination=CursorPagination(), meta=ResponseMeta(request_id="req")
    )
    assert value.model_dump(mode="json")["pagination"] == {"next_cursor": None, "has_more": False}
    with pytest.raises(ValidationError):
        CursorPagination(has_more=True)
    with pytest.raises(ValidationError):
        CursorPagination(next_cursor="cursor", has_more=False)
