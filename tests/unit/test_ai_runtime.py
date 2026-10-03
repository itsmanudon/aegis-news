import re
from types import SimpleNamespace

import pytest


class Tokenizer:
    model_max_length = 256
    is_fast = True

    def __call__(self, text, **kwargs):
        return {"offset_mapping": [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]}

    def encode(self, text, **kwargs):
        return list(range(len(text.split())))


def test_token_chunks_preserve_all_words_and_offsets():
    from aegis.intelligence.local_runtime import token_chunks

    text = "alpha beta\n gamma delta epsilon"
    chunks = token_chunks(Tokenizer(), text, 2)
    assert chunks == [("alpha beta", 0), ("gamma delta", 12), ("epsilon", 24)]
    assert " ".join(c for c, _ in chunks).split() == text.split()


def test_chunk_retokenization_cannot_silently_exceed_model_limit():
    from aegis.intelligence.local_runtime import token_chunks

    class BoundaryTokenizer(Tokenizer):
        def encode(self, text, **kwargs):
            # Some tokenizers produce extra pieces when a substring loses word context.
            return [0] * (len(text.split()) + 1)

    tokenizer = BoundaryTokenizer()
    chunks = token_chunks(tokenizer, "a b c d", 2)
    assert " ".join(c for c, _ in chunks) == "a b c d"
    assert all(len(tokenizer.encode(chunk)) <= 2 for chunk, _ in chunks)


def test_zero_shot_tasks_share_one_loaded_model(monkeypatch):
    import sys

    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.local_runtime import LocalRuntime

    class Factory:
        @staticmethod
        def from_pretrained(name, **kwargs):
            return Tokenizer() if kwargs.get("use_fast") else object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=Factory,
            AutoModelForTokenClassification=Factory,
            AutoModelForSequenceClassification=Factory,
            pipeline=lambda task, **kwargs: SimpleNamespace(tokenizer=Tokenizer()),
        ),
    )
    runtime = LocalRuntime()
    spec = ModelSpec(backend="transformers", model_name="zero-shot", revision="a" * 40)
    topics = runtime._load("topic", spec)
    events = runtime._load("event_extraction", spec)
    classification = runtime._load("event_classification", spec)
    assert topics is events is classification


async def test_local_ner_rejects_lossy_or_out_of_chunk_offsets(news_document, monkeypatch):
    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.errors import InvalidPrediction
    from aegis.intelligence.local_runtime import LocalRuntime
    from aegis.intelligence.providers import Entities

    class Model:
        tokenizer = Tokenizer()

        def __init__(self, start, end):
            self.start, self.end = start, end

        def __call__(self, text, **kwargs):
            return [{"start": self.start, "end": self.end, "entity_group": "ORG", "score": 0.8}]

    runtime = LocalRuntime()
    spec = ModelSpec(backend="transformers", model_name="small-test", revision="a" * 40)
    for start, end in ((0.2, 9.9), (0, len(news_document.text) + 10)):
        model = Model(start, end)
        monkeypatch.setattr(runtime, "_load", lambda task, spec, loaded=model: loaded)
        with pytest.raises(InvalidPrediction):
            await Entities(spec, runtime).extract(news_document)


async def test_transformer_loader_uses_pinned_offline_models(news_document, monkeypatch):
    import sys

    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.local_runtime import LocalRuntime
    from aegis.intelligence.providers import Entities, Sentiment, Topics

    class Factory:
        @staticmethod
        def from_pretrained(name, **kwargs):
            assert kwargs["revision"] == "a" * 40
            assert kwargs["local_files_only"] is True
            assert kwargs["trust_remote_code"] is False
            return Tokenizer() if kwargs.get("use_fast") else object()

    class Pipeline:
        tokenizer = Tokenizer()

        def __init__(self, task):
            self.task = task

        def __call__(self, text, **kwargs):
            if self.task == "token-classification":
                return [{"start": 0, "end": 9, "entity_group": "ORG", "score": 0.8}]
            if self.task == "text-classification":
                return [
                    {"label": "positive", "score": 0.8},
                    {"label": "negative", "score": 0.1},
                    {"label": "neutral", "score": 0.1},
                ]
            return {"labels": ["technology.ai", "general"], "scores": [0.9, 0.1]}

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=Factory,
            AutoModelForTokenClassification=Factory,
            AutoModelForSequenceClassification=Factory,
            pipeline=lambda task, **kwargs: Pipeline(task),
        ),
    )
    runtime = LocalRuntime()
    spec = ModelSpec(backend="transformers", model_name="small-test-double", revision="a" * 40)
    ner = await Entities(spec, runtime).extract(news_document)
    sentiment = await Sentiment(spec, runtime).analyze(news_document)
    topic = await Topics(spec, runtime).classify(news_document)
    assert ner.outputs[0].surface == "Acme Labs"
    assert ner.provider == "local-transformers"
    assert sentiment.outputs[0].score == pytest.approx(0.7)
    assert topic.outputs[0].label == "technology.ai"


@pytest.fixture
def news_document(document):
    return document.model_copy(update={"text": "Acme Labs uses artificial intelligence."})


async def test_embedding_runtime_chunks_and_normalizes(news_document, monkeypatch):
    import sys

    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.local_runtime import LocalRuntime
    from aegis.intelligence.providers import Embeddings

    class Matrix(list):
        shape = (2, 2)

    class Model:
        tokenizer = Tokenizer()
        max_seq_length = 6

        def __init__(self, name, **kwargs):
            assert kwargs["revision"] == "b" * 40
            assert kwargs["local_files_only"] is True

        def encode(self, chunks, **kwargs):
            assert chunks == ["Acme Labs uses artificial", "intelligence."]
            return Matrix([[1.0, 0.0], [0.0, 1.0]])

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=Model)
    )
    spec = ModelSpec(
        backend="sentence-transformers", model_name="small-double", revision="b" * 40, dimensions=2
    )
    result = await Embeddings(spec, LocalRuntime()).embed(news_document)
    assert result.outputs[0].values == pytest.approx((4 / 17**0.5, 1 / 17**0.5))


async def test_inference_failure_and_missing_model_are_explicit(document, monkeypatch):
    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.errors import IntelligenceError, ModelUnavailable
    from aegis.intelligence.local_runtime import LocalRuntime
    from aegis.intelligence.providers import Embeddings, Topics

    class Failed:
        metadata = {}

        def predict(self, *args):
            raise RuntimeError("failed")

    with pytest.raises(IntelligenceError, match="inference failed"):
        await Topics(
            ModelSpec(backend="baseline", model_name="bad", revision="1"), Failed()
        ).classify(document)

    import importlib

    original = importlib.import_module

    def missing(name, *args):
        if name == "sentence_transformers":
            raise ImportError("not installed")
        return original(name, *args)

    monkeypatch.setattr(importlib, "import_module", missing)
    with pytest.raises(ModelUnavailable):
        await Embeddings(
            ModelSpec(backend="sentence-transformers", model_name="missing", revision="c" * 40),
            LocalRuntime(),
        ).embed(document)
