"""Export checked-in contracts. --check fails on drift without writing."""

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from aegis.contracts.api import ApiErrorEnvelope, CollectionResponse, SingleResponse
from aegis.contracts.events import EVENT_MODELS, AsyncEvent
from aegis.domain import models
from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def generated_schemas() -> dict[Path, str]:
    schemas: dict[Path, object] = {
        Path("schemas/openapi/v1.json"): create_app().openapi(),
        Path("schemas/events/envelope.v1.json"): TypeAdapter(AsyncEvent).json_schema(),
        Path("schemas/api-error.v1.json"): ApiErrorEnvelope.model_json_schema(),
        Path("schemas/api-single.v1.json"): SingleResponse[models.NewsDocument].model_json_schema(),
        Path("schemas/api-collection.v1.json"): CollectionResponse[
            models.NewsDocument
        ].model_json_schema(),
    }
    for event in EVENT_MODELS:
        schemas[Path(f"schemas/events/{event.model_fields['event_type'].default}.json")] = (
            event.model_json_schema()
        )
    for name in (
        "Source",
        "RawIngestion",
        "MediaAsset",
        "DocumentMediaLink",
        "NewsDocument",
        "Entity",
        "EntityMention",
        "AssetMapping",
        "TopicResult",
        "SentimentResult",
        "EntityExtractionResult",
        "EntityResolutionResult",
        "EmbeddingResult",
        "EventExtractionResult",
        "EventClassificationResult",
        "AnalysisResult",
        "NewsEvent",
        "ProvenanceRecord",
    ):
        model: type[BaseModel] = getattr(models, name)
        schemas[Path(f"schemas/domain/{name}.v1.json")] = model.model_json_schema()
    return {
        path: json.dumps(schema, indent=2, sort_keys=True) + "\n"
        for path, schema in schemas.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, value in generated_schemas().items():
        destination = ROOT / path
        if args.check:
            if not destination.exists() or destination.read_text() != value:
                raise SystemExit(
                    f"Schema drift: {path}; run uv run python scripts/export_schemas.py"
                )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value)


if __name__ == "__main__":
    main()
