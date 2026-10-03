"""Immutable model registry. Model loading is always explicit and lazy."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    backend: Literal["baseline", "transformers", "sentence-transformers"]
    model_name: str = Field(min_length=1, max_length=512)
    revision: str = Field(min_length=1, max_length=512)
    dimensions: int = Field(default=64, ge=1, le=8192)
    device: str = "cpu"
    local_files_only: bool = True
    max_tokens: int = Field(default=256, ge=8, le=512)
    threshold: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def pinned(self) -> Self:
        if self.backend != "baseline" and (
            len(self.revision) != 40 or any(c not in "0123456789abcdef" for c in self.revision)
        ):
            raise ValueError("downloadable models require an immutable commit SHA")
        return self


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ner: ModelSpec
    topic: ModelSpec
    sentiment: ModelSpec
    embedding: ModelSpec
    event: ModelSpec


def profile(name: str) -> Profile:
    def baseline(model: str) -> ModelSpec:
        return ModelSpec(backend="baseline", model_name=model, revision="1")

    if name == "offline":
        return Profile(
            ner=baseline("capitalized-spans"),
            topic=baseline("keyword-topics"),
            sentiment=baseline("lexicon-sentiment"),
            embedding=baseline("hash-vectors"),
            event=baseline("keyword-events"),
        )
    if name not in ("light", "full"):
        raise ValueError(f"unknown resource profile: {name}")
    ner = ModelSpec(
        backend="transformers",
        model_name="dslim/bert-base-NER",
        revision="d1a3e8f13f8c3566299d95fcfc9a8d2382a9affc",
    )
    sentiment = ModelSpec(
        backend="transformers",
        model_name="ProsusAI/finbert",
        revision="4556d13015211d73dccd3fdd39d39232506f3e43",
    )
    embedding = ModelSpec(
        backend="sentence-transformers",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        dimensions=384,
    )
    topic, event = baseline("keyword-topics"), baseline("keyword-events")
    if name == "full":
        topic = event = ModelSpec(
            backend="transformers",
            model_name="facebook/bart-large-mnli",
            revision="d7645e127eaf1aefc7862fd59a17a5aa8558b8ce",
        )
        embedding = ModelSpec(
            backend="sentence-transformers",
            model_name="sentence-transformers/all-mpnet-base-v2",
            revision="e8c3b32edf5434bc2275fc9bab85f82640a19130",
            dimensions=768,
        )
    return Profile(ner=ner, sentiment=sentiment, topic=topic, event=event, embedding=embedding)
