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
            if spec.model_name == "name-spans":
                return [
                    {"surface": surface, "start": start, "end": end, "kind": "other", "score": 0.55}
                    for surface, start, end in name_spans(text)
                ]
            # capitalized-spans, revision 1: the public headline baseline pins it.
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


# A name word starts with a capital and may continue with letters, digits and the
# joiners companies use ("AT&T", "Coca-Cola", "Amazon.com"); "NVIDIA" and "JPMorgan"
# qualify. This is the "name-spans" extractor (16 Nov 2026). The older
# "capitalized-spans" matched only runs of two or more capitalised words, so "Apple",
# "Nvidia" or "Bank of America" were never extracted and no general news story
# resolved to a company; it stays, unchanged, for the public headline baseline.
_NAME_WORD = r"[A-Z][A-Za-z0-9]*(?:[&'.\-][A-Za-z0-9]+)*"
# Small words a name may contain between capitalised words.
_JOINERS = r"(?:of|and|&|the|de|du)"
_NAME_RUN = re.compile(
    rf"(?<![\w&'.\-]){_NAME_WORD}(?:\s+(?:{_JOINERS}\s+)?{_NAME_WORD})*(?![\w&'-])"
)
_TOKEN = re.compile(rf"{_NAME_WORD}|{_JOINERS}")
MAX_SPAN_WORDS = 6
# Revision 2 (16 Nov 2026): phrases whose capitalised words are not company names.
# Title-case finance headlines write "Price Target", and "Target" alone resolved to
# Target Corporation (4 of 43 stored headlines). A part of a run that lies wholly
# inside one of these phrases is not offered; the whole run still is.
NON_NAME_PHRASES = frozenset(
    {
        ("price", "target"),
        ("price", "targets"),
        ("target", "price"),
        ("target", "prices"),
        ("target", "date"),
        ("target", "range"),
        ("target", "rate"),
        ("on", "target"),
    }
)


def name_spans(text: str) -> list[tuple[str, int, int]]:
    """Every run of capitalised words and every contiguous part of it.

    The resolver keeps only the parts that equal a known company's name or alias,
    so "Shares of Home Depot" yields "Home Depot" and "Apple Inc" yields both
    "Apple Inc" and "Apple". A part never starts or ends on a joiner. Each span is
    returned once, with offsets into ``text``.
    """
    spans: dict[tuple[int, int], str] = {}
    for run in _NAME_RUN.finditer(text):
        tokens = [
            (m.group(), run.start() + m.start(), run.start() + m.end())
            for m in _TOKEN.finditer(run.group())
        ]
        # Token indexes covered by a non-name phrase, one set per occurrence.
        phrases = [
            set(range(k, k + len(phrase)))
            for k in range(len(tokens))
            for phrase in NON_NAME_PHRASES
            if tuple(t.lower() for t, _, _ in tokens[k : k + len(phrase)]) == phrase
        ]
        for i, (first, start, _) in enumerate(tokens):
            if re.fullmatch(_JOINERS, first):
                continue
            words = 0
            for j in range(i, len(tokens)):
                last, _, end = tokens[j]
                if re.fullmatch(_JOINERS, last):
                    continue
                words += 1
                if words > MAX_SPAN_WORDS:
                    break
                inside = set(range(i, j + 1))
                if any(inside < phrase for phrase in phrases):
                    continue
                if end - start <= 512:
                    spans[(start, end)] = text[start:end]
    return [(surface, start, end) for (start, end), surface in sorted(spans.items())]
