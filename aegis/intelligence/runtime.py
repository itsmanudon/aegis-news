"""Offline task baselines and a small swappable inference runtime port."""

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from aegis.intelligence.config import ModelSpec
from aegis.intelligence.taxonomy import EVENTS, NEGATIVE, POSITIVE, TOPICS

Prediction = Mapping[str, Any]


class Runtime(Protocol):
    @property
    def metadata(self) -> dict[str, str]: ...

    def predict(
        self, task: str, text: str, spec: ModelSpec, labels: tuple[str, ...] = ()
    ) -> Sequence[Prediction]: ...


def keyword_scores(text: str, taxonomy: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    scores = []
    for label, words in taxonomy.items():
        count = sum(
            len(re.findall(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text.lower())) for w in words
        )
        if count:
            scores.append({"label": label, "score": min(0.95, 0.55 + 0.1 * count)})
    return sorted(scores, key=lambda x: -x["score"])


def normalize_vector(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values] if norm else list(values)


class BaselineRuntime:
    metadata = {"baseline": "1"}

    def predict(
        self, task: str, text: str, spec: ModelSpec, labels: tuple[str, ...] = ()
    ) -> Sequence[Prediction]:
        if task == "entity_extraction":
            return [
                {
                    "surface": m.group(),
                    "start": m.start(),
                    "end": m.end(),
                    "kind": "other",
                    "score": 0.55,
                }
                for m in re.finditer(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b", text)
                if len(m.group()) <= 512
            ]
        if task == "topic":
            return keyword_scores(text, TOPICS)[:1] or [{"label": "general", "score": 0.5}]
        if task in ("event_extraction", "event_classification"):
            return keyword_scores(text, EVENTS) or (
                [{"label": "general", "score": 0.5}] if task == "event_classification" else []
            )
        if task == "sentiment":
            words = re.findall(r"\w+", text.lower())
            positive, negative = (
                sum(w in POSITIVE for w in words),
                sum(w in NEGATIVE for w in words),
            )
            label = (
                "mixed"
                if positive and negative
                else ("positive" if positive else "negative" if negative else "neutral")
            )
            return [{"label": label, "score": 0.6}]
        if task == "embedding":
            # Wiring baseline only: deterministic token hashing is not semantic embedding.
            values = [0.0] * spec.dimensions
            for word in re.findall(r"\w+", text.lower()):
                digest = hashlib.sha256(word.encode()).digest()
                values[int.from_bytes(digest[:4]) % spec.dimensions] += 1 if digest[4] % 2 else -1
            return [{"values": normalize_vector(values)}]
        raise ValueError(f"unsupported task: {task}")
