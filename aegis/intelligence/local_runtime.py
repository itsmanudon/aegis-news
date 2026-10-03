"""Lazy, cached local Hugging Face inference; imports never download weights."""

import importlib
import operator
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from threading import RLock
from typing import Any

from aegis.intelligence.config import ModelSpec
from aegis.intelligence.errors import InvalidPrediction, ModelUnavailable
from aegis.intelligence.runtime import Prediction, normalize_vector


def token_chunks(tokenizer: Any, text: str, limit: int) -> list[tuple[str, int]]:
    """Keep original character offsets and every token, including long documents."""
    if limit < 1:
        raise ValueError("positive token limit required")
    offsets = tokenizer(
        text, add_special_tokens=False, return_offsets_mapping=True, truncation=False
    )["offset_mapping"]
    if not offsets:
        return [(text, 0)]
    chunks = []
    start = 0
    while start < len(offsets):
        left = offsets[start][0]
        end = min(start + limit, len(offsets))
        right = offsets[end - 1][1]
        # Retokenizing a mid-word substring can change its piece count. Reduce the
        # window until the actual text passed to inference fits, rather than relying
        # on SentenceTransformer's internal truncation.
        while len(tokenizer.encode(text[left:right], add_special_tokens=False)) > limit:
            end -= 1
            if end <= start:
                raise ValueError("a token cannot fit the configured inference window")
            right = offsets[end - 1][1]
        chunks.append((text[left:right], left))
        start = end
    return chunks


class LocalRuntime:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], Any] = {}
        # Serialize inference per runtime; torch pipelines need not be thread safe.
        self._lock = RLock()

    @property
    def metadata(self) -> dict[str, str]:
        result = {}
        for package in ("transformers", "sentence-transformers", "torch", "tokenizers"):
            try:
                result[package] = version(package)
            except PackageNotFoundError:
                result[package] = "uninstalled"
        return result

    def _load(self, task: str, spec: ModelSpec) -> Any:
        family = (
            "zero-shot" if task in ("topic", "event_extraction", "event_classification") else task
        )
        key = (family, spec.model_dump_json())
        if key in self._cache:
            return self._cache[key]
        try:
            if task == "embedding":
                sentence_transformers = importlib.import_module("sentence_transformers")
                model = sentence_transformers.SentenceTransformer(
                    spec.model_name,
                    revision=spec.revision,
                    device=spec.device,
                    trust_remote_code=False,
                    local_files_only=spec.local_files_only,
                )
            else:
                transformers = importlib.import_module("transformers")

                kwargs = {
                    "revision": spec.revision,
                    "local_files_only": spec.local_files_only,
                    "trust_remote_code": False,
                }
                tokenizer = transformers.AutoTokenizer.from_pretrained(
                    spec.model_name, use_fast=True, **kwargs
                )
                if not tokenizer.is_fast:
                    raise ModelUnavailable("NER/chunking requires a fast offset-aware tokenizer")
                factory = (
                    transformers.AutoModelForTokenClassification
                    if task == "entity_extraction"
                    else transformers.AutoModelForSequenceClassification
                )
                weights = factory.from_pretrained(spec.model_name, **kwargs)
                pipeline_task = (
                    "token-classification"
                    if task == "entity_extraction"
                    else "text-classification"
                    if task == "sentiment"
                    else "zero-shot-classification"
                )
                model = transformers.pipeline(
                    pipeline_task, model=weights, tokenizer=tokenizer, device=spec.device
                )
            self._cache[key] = model
            return model
        except ModelUnavailable:
            raise
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            raise ModelUnavailable(
                "local model unavailable; install optional dependencies and explicitly download "
                "the configured revision before running offline"
            ) from exc

    def predict(
        self, task: str, text: str, spec: ModelSpec, labels: tuple[str, ...] = ()
    ) -> Sequence[Prediction]:
        with self._lock:
            model = self._load(task, spec)
            tokenizer = model.tokenizer
            limit = min(spec.max_tokens, int(tokenizer.model_max_length)) - 2
            if task == "embedding":
                limit = min(limit, int(model.max_seq_length) - 2)
            elif task in ("topic", "event_extraction", "event_classification"):
                # Zero-shot adds a hypothesis; reserve enough room and never truncate premise.
                limit -= (
                    max(len(tokenizer.encode(f"This text is about {label}.")) for label in labels)
                    + 4
                )
            if limit < 1:
                raise ValueError("max_tokens too small for configured labels")
            chunks = token_chunks(tokenizer, text, limit)
            if task == "entity_extraction":
                predictions = []
                kinds = {"ORG": "organization", "PER": "person", "LOC": "location"}
                for chunk, offset in chunks:
                    for item in model(chunk, aggregation_strategy="simple"):
                        try:
                            start, end = operator.index(item["start"]), operator.index(item["end"])
                        except (KeyError, TypeError) as exc:
                            raise InvalidPrediction("NER offsets must be integers") from exc
                        if not 0 <= start < end <= len(chunk):
                            raise InvalidPrediction("NER offsets exceed inference chunk bounds")
                        start, end = start + offset, end + offset
                        predictions.append(
                            {
                                "surface": text[start:end],
                                "start": start,
                                "end": end,
                                "kind": kinds.get(item["entity_group"], "other"),
                                "score": float(item["score"]),
                            }
                        )
                return predictions
            if task == "embedding":
                # Weighted mean of sentence/chunk vectors, followed by unit normalization.
                vectors = model.encode(
                    [c for c, _ in chunks],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                if vectors.shape[1] != spec.dimensions:
                    raise ValueError("configured embedding dimensions do not match model")
                weights = [len(tokenizer.encode(c, add_special_tokens=False)) for c, _ in chunks]
                total = max(sum(weights), 1)
                values = [
                    sum(float(v[i]) * w for v, w in zip(vectors, weights, strict=True)) / total
                    for i in range(spec.dimensions)
                ]
                return [{"values": normalize_vector(values)}]
            aggregate: dict[str, float] = {}
            total_weight = 0
            for chunk, _ in chunks:
                weight = max(len(tokenizer.encode(chunk, add_special_tokens=False)), 1)
                if task == "sentiment":
                    items = model(chunk, top_k=None, truncation=False)
                else:
                    raw = model(
                        chunk,
                        candidate_labels=list(labels),
                        multi_label=True,
                        hypothesis_template="This text is about {}.",
                    )
                    items = [
                        {"label": label, "score": score}
                        for label, score in zip(raw["labels"], raw["scores"], strict=True)
                    ]
                for item in items:
                    label = str(item["label"]).lower()
                    aggregate[label] = aggregate.get(label, 0) + float(item["score"]) * weight
                total_weight += weight
            return sorted(
                [
                    {"label": label, "score": score / total_weight}
                    for label, score in aggregate.items()
                ],
                key=lambda item: -item["score"],
            )
