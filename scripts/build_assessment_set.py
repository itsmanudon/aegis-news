"""Rebuild original CC0 texts and manually authored labels, never from predictions."""

import json
import struct
import zlib
from pathlib import Path
from typing import Any

from aegis.intelligence.pipeline import stable_id

ROOT = Path(__file__).resolve().parents[1]
TIME = "2024-01-01T00:00:00Z"
# Text, category, topic, sentiment and event labels are authored together before inference.
ROWS = (
    (
        "Atlas Labs",
        "business",
        "Atlas Labs reported quarterly earnings with strong profit growth.",
        "business.earnings",
        "positive",
        "company.earnings",
    ),
    (
        "Meridian Works",
        "business",
        "Meridian Works posted a quarterly revenue surplus after costs improved.",
        "business.earnings",
        "positive",
        "company.earnings",
    ),
    (
        "Delta Bank",
        "economics",
        "Delta Bank announced an interest rate hike as inflation rose.",
        "economy",
        "neutral",
        "economy.rate_change",
    ),
    (
        "Reserve Council",
        "economics",
        "Reserve Council reduced borrowing costs to support the economy.",
        "economy",
        "positive",
        "economy.rate_change",
    ),
    (
        "Pixel Forge",
        "technology",
        "Pixel Forge launched new artificial intelligence software with improved reliability.",
        "technology.ai",
        "positive",
        "company.product_launch",
    ),
    (
        "Orion Systems",
        "technology",
        "Orion Systems unveiled a machine learning tool after a failed trial. "
        "IBM supported the launch.",
        "technology.ai",
        "mixed",
        "company.product_launch",
    ),
    (
        "River Parliament",
        "public-policy",
        "River Parliament passed legislation and a new law on water permits.",
        "politics.policy",
        "neutral",
        "policy.change",
    ),
    (
        "Metro Council",
        "public-policy",
        "Metro Council adopted a public policy change to protect drinking water.",
        "politics/public-policy",
        "positive",
        "policy.change",
    ),
    (
        "Harbor Council",
        "regional",
        "Harbor Council opened a regional library for local residents.",
        "regional",
        "positive",
        "general",
    ),
    (
        "Cedar District",
        "regional",
        "Cedar District repaired municipal roads after storm damage.",
        "regional",
        "mixed",
        "general",
    ),
    (
        "Copper Basin",
        "commodity",
        "Copper Basin reported a mine closure and supply disruption after a pipeline outage.",
        "commodities",
        "negative",
        "commodity.supply_disruption",
    ),
    (
        "Wheat Cooperative",
        "commodity",
        "Wheat Cooperative halted grain deliveries after floods.",
        "commodities",
        "negative",
        "commodity.supply_disruption",
    ),
    (
        "Secure Harbor",
        "cyber-security",
        "Secure Harbor confirmed a ransomware data breach in its software.",
        "technology",
        "negative",
        "security.cyber_incident",
    ),
    (
        "Beacon Network",
        "cyber-security",
        "Beacon Network restored services after a cyberattack caused failure.",
        "technology",
        "mixed",
        "security.cyber_incident",
    ),
    (
        "City Museum",
        "media",
        "City Museum unveiled a technology exhibit with a regional illustration.",
        "regional",
        "neutral",
        "company.product_launch",
    ),
    (
        "Valley Gallery",
        "media",
        "Valley Gallery opened a municipal photo exhibition showing improved access.",
        "regional",
        "positive",
        "general",
    ),
)


def image_bytes() -> bytes:
    """Original schematic bar illustration, RGB PNG; no external artwork."""
    width, height = 320, 160
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            bar = any(
                left <= x < left + 45 and top <= y < 140
                for left, top in ((40, 95), (135, 65), (230, 35))
            )
            pixels.extend((38, 113, 91) if bar else (240, 243, 237))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    cases: list[dict[str, Any]] = []
    for i, (name, category, text, topic, sentiment, event) in enumerate(ROWS):
        document_id = stable_id("doc", f"assessment:{i}")
        entity_id = stable_id("ent", f"assessment:{name}")
        candidate = {
            "entity_id": entity_id,
            "canonical_name": name,
            "kind": "organization",
            "created_at": TIME,
        }
        mentions: list[dict[str, Any]] = [
            {
                "extraction": {
                    "surface": name,
                    "start_offset": text.index(name),
                    "end_offset": text.index(name) + len(name),
                    "predicted_kind": "organization",
                    "confidence": 1.0,
                },
                "entity_id": entity_id,
            }
        ]
        candidates = [candidate]
        if name == "Metro Council":
            candidates.append(
                {**candidate, "entity_id": stable_id("ent", "assessment:ambiguous-metro")}
            )
            mentions[0]["entity_id"] = None
        if "IBM" in text:
            mentions.append(
                {
                    "extraction": {
                        "surface": "IBM",
                        "start_offset": text.index("IBM"),
                        "end_offset": text.index("IBM") + 3,
                        "predicted_kind": "organization",
                        "confidence": 1.0,
                    },
                    "entity_id": None,
                }
            )
        cases.append(
            {
                "sample": {
                    "document": {
                        "document_id": document_id,
                        "ingestion_id": stable_id("ing", f"assessment:{i}"),
                        "source_id": stable_id("src", "assessment"),
                        "title": f"Synthetic {category}: {name}",
                        "text": text,
                        "language": "en",
                        "published_at": "2020-01-01T00:00:00Z",
                        "first_seen_at": TIME,
                        "ingested_at": TIME,
                        "created_at": TIME,
                    },
                    "mentions": mentions,
                    "candidates": candidates,
                    "topic": topic,
                    "sentiment": sentiment,
                    "event": event,
                    "event_summary": text.split(". ")[0].rstrip(".") + ".",
                },
                "category": category,
                "expected_events": []
                if event == "general"
                else [
                    {"event_type": event, "evidence_text": text.split(". ")[0].rstrip(".") + "."}
                ],
                "relevant_documents": [
                    stable_id("doc", f"assessment:{i + 1 if i % 2 == 0 else i - 1}")
                ],
                "media_path": "data/samples/demo-image.png" if category == "media" else None,
                "annotation_note": (
                    "Overall reported outcome; mixed means adverse event plus recovery/benefit. "
                    "Organization types use real semantic labels, not baseline output. "
                    "Topic is the primary subject; paired category document is a coarse "
                    "retrieval relevance judgment."
                ),
            }
        )
    payload = {
        "version": "assessment-v1",
        "license": "CC0-1.0",
        "annotation_status": (
            "Agent-authored and manually inspected; independent human adjudication pending"
        ),
        "cases": cases,
    }
    target = ROOT / "ml/datasets/gold/assessment-v1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (ROOT / "data/samples/demo-image.png").write_bytes(image_bytes())


if __name__ == "__main__":
    main()
