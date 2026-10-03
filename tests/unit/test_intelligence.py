import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aegis.domain.ids import new_id
from aegis.domain.models import Entity, NewsEvent


def engine():
    from aegis.intelligence.engine import build_engine

    return build_engine("offline")


@pytest.fixture
def news(document):
    return document.model_copy(
        update={"text": "Acme Labs reported earnings growth and strong profit."}
    )


async def test_typed_pipeline_and_envelope_metadata(news):
    ai = engine()
    before = datetime.now(UTC)
    results = [
        await ai.entities.extract(news),
        await ai.topics.classify(news),
        await ai.sentiment.analyze(news),
        await ai.embeddings.embed(news),
        await ai.events.extract(news, ()),
    ]
    assert [r.analysis_type for r in results] == [
        "entity_extraction",
        "topic",
        "sentiment",
        "embedding",
        "event_extraction",
    ]
    for result in results:
        assert result.document_id == news.document_id
        assert result.analysis_id.startswith("ana_")
        assert result.provider == "local-baseline"
        assert result.model_version
        assert len(result.configuration_hash) == 64
        assert before <= result.created_at <= result.available_at <= datetime.now(UTC)
        assert all(o.result_type == result.analysis_type for o in result.outputs)
        with pytest.raises(ValidationError):
            result.provider = "changed"
        assert type(result).model_validate_json(result.model_dump_json()) == result
    span = results[0].outputs[0]
    assert news.text[span.start_offset : span.end_offset] == span.surface == "Acme Labs"
    assert results[1].outputs[0].label == "business.earnings"
    assert results[2].outputs[0].label == "positive"
    assert len(results[3].outputs[0].values) == 64
    assert results[4].outputs[0].proposed_event_type == "company.earnings"


async def test_hash_changes_with_effective_configuration(news):
    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.providers import Embeddings
    from aegis.intelligence.runtime import BaselineRuntime

    a = ModelSpec(backend="baseline", model_name="hash", revision="1", dimensions=8)
    b = a.model_copy(update={"dimensions": 16})
    x = await Embeddings(a, BaselineRuntime()).embed(news)
    y = await Embeddings(b, BaselineRuntime()).embed(news)
    z = await Embeddings(a, BaselineRuntime()).embed(news)
    assert x.configuration_hash == z.configuration_hash != y.configuration_hash
    assert x.analysis_id != z.analysis_id
    assert len(x.outputs[0].values) == 8


async def test_provider_swap_and_completion_time(news):
    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.providers import Sentiment

    class Delayed:
        metadata = {"test-runtime": "1"}

        def predict(self, task, text, spec, labels=()):
            import time

            time.sleep(0.01)
            return [{"label": "negative", "score": 0.8}]

    provider = Sentiment(
        ModelSpec(backend="baseline", model_name="swapped", revision="2"), Delayed()
    )
    result = await provider.analyze(news)
    assert result.outputs[0].label == "negative"
    assert result.outputs[0].score == -0.8
    assert result.model_name == "swapped"
    assert result.model_version == "2"
    assert result.available_at > result.created_at


async def test_failures_do_not_fabricate_outputs(document):
    from aegis.intelligence.errors import NoPredictions, UnsupportedLanguage

    ai = engine()
    with pytest.raises(NoPredictions):
        await ai.entities.extract(document.model_copy(update={"text": "nothing found"}))
    with pytest.raises(NoPredictions):
        await ai.events.extract(document, ())
    with pytest.raises(UnsupportedLanguage):
        await ai.topics.classify(document.model_copy(update={"language": "hi"}))


async def test_invalid_vectors_and_spans_fail(news):
    from aegis.intelligence.config import ModelSpec
    from aegis.intelligence.errors import InvalidPrediction
    from aegis.intelligence.providers import Embeddings, Entities

    class Bad:
        metadata = {}

        def predict(self, task, text, spec, labels=()):
            if task == "embedding":
                return [{"values": [float("nan"), 0.0]}]
            return [
                {"surface": "wrong", "start": 0, "end": 4, "kind": "organization", "score": 0.7}
            ]

    spec = ModelSpec(backend="baseline", model_name="bad", revision="1", dimensions=2)
    with pytest.raises(InvalidPrediction):
        await Embeddings(spec, Bad()).embed(news)
    with pytest.raises(InvalidPrediction):
        await Entities(spec, Bad()).extract(news)


async def test_event_classification_preserves_revision(news, now):
    event = NewsEvent(
        event_id=new_id("evt"),
        revision=7,
        summary="Acme Labs earnings",
        document_ids=(news.document_id,),
        created_at=now,
        available_at=now,
        evidence_kind="fact",
    )
    result = await engine().events.classify(news, event)
    assert result.analysis_type == "event_classification"
    assert result.outputs[0].event_id == event.event_id
    assert result.outputs[0].event_revision == 7
    assert result.outputs[0].label == "company.earnings"
    with pytest.raises(ValueError):
        await engine().events.classify(
            news, event.model_copy(update={"document_ids": (new_id("doc"),)})
        )


async def test_resolver_alias_ambiguity_unknown_and_lineage(news, now):
    from aegis.entities.materialize import materialize_mentions
    from aegis.intelligence.resolution import Resolver

    extraction = await engine().entities.extract(news)
    mentions = materialize_mentions(news, extraction)
    assert mentions[0].analysis_id == extraction.analysis_id
    assert mentions[0].evidence_kind == "model_output"
    assert materialize_mentions(news, extraction) == mentions
    a = Entity(
        entity_id=new_id("ent"), canonical_name="Acme Research", kind="organization", created_at=now
    )
    b = a.model_copy(update={"entity_id": new_id("ent"), "canonical_name": "Other Labs"})
    resolver = Resolver(aliases={a.entity_id: ("Acme Labs",)})
    resolved = await resolver.resolve(news, mentions, (a, b))
    assert resolved.outputs[0].entity_id == a.entity_id
    ambiguous = await Resolver(
        aliases={a.entity_id: ("Acme Labs",), b.entity_id: ("Acme Labs",)}
    ).resolve(news, mentions, (a, b))
    assert ambiguous.outputs[0].entity_id is None
    unknown = await resolver.resolve(news, mentions, ())
    assert unknown.outputs[0].entity_id is None
    with pytest.raises(ValueError):
        await resolver.resolve(
            news, (mentions[0].model_copy(update={"document_id": new_id("doc")}),), (a,)
        )


async def test_activities_offline_without_network(news, monkeypatch):
    import socket

    from aegis.entities.materialize import materialize_mentions
    from apps.worker.ai_activities import AIActivities, EventRequest, ResolutionRequest

    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    activities = AIActivities(engine())
    entities = await activities.analyze_entities(news)
    outputs = await asyncio.gather(
        activities.analyze_topics(news),
        activities.analyze_sentiment(news),
        activities.generate_embedding(news),
        activities.extract_events(EventRequest(document=news)),
        activities.resolve_entities(
            ResolutionRequest(document=news, mentions=materialize_mentions(news, entities))
        ),
    )
    assert len(outputs) == 5
    assert len(activities.registered()) == 7


def test_profiles_pin_revisions_and_offline_defaults():
    from aegis.intelligence.config import ModelSpec, profile

    for name in ("light", "full"):
        specs = profile(name)
        assert specs.embedding.dimensions in (384, 768)
        for spec in (specs.ner, specs.sentiment, specs.topic, specs.event, specs.embedding):
            assert spec.local_files_only
            if spec.backend != "baseline":
                assert len(spec.revision) == 40
    with pytest.raises(ValidationError):
        ModelSpec(backend="transformers", model_name="remote", revision="main")


async def test_targeted_sentiment_uses_entity_sentence_context(news, now):
    from aegis.domain.models import EntityMention
    from aegis.intelligence.config import profile
    from aegis.intelligence.providers import Sentiment
    from aegis.intelligence.runtime import BaselineRuntime

    document = news.model_copy(
        update={"text": "Acme Labs had strong growth. Orion Works reported losses."}
    )
    entity = Entity(
        entity_id=new_id("ent"), canonical_name="Orion Works", kind="organization", created_at=now
    )
    mention = EntityMention(
        mention_id=new_id("mention"),
        document_id=document.document_id,
        surface="Orion Works",
        start_offset=29,
        end_offset=40,
        entity_id=entity.entity_id,
        evidence_kind="fact",
    )
    result = await Sentiment(profile("offline").sentiment, BaselineRuntime()).analyze_entity(
        document, entity, (mention,)
    )
    assert result.outputs[0].label == "negative"
    assert result.outputs[0].entity_id == entity.entity_id


def test_resolver_normalization_identifiers_fuzzy_and_short_names(now):
    from aegis.intelligence.resolution import Resolver

    entity = Entity(
        entity_id=new_id("ent"), canonical_name="Acme Research", kind="organization", created_at=now
    )
    resolver = Resolver(identifiers={entity.entity_id: ("synthetic-id-123",)})
    for surface in ("ACME, RESEARCH", "Acme Reseach", "synthetic-id-123"):
        assert resolver.choose(resolver.rank(surface, (entity,)))[0] == entity.entity_id
    assert resolver.choose(resolver.rank("Ac", (entity,)))[0] is None


async def test_invalid_confidence_is_not_filtered_away(news):
    from aegis.intelligence.config import profile
    from aegis.intelligence.errors import InvalidPrediction
    from aegis.intelligence.providers import Entities

    class Bad:
        metadata = {}

        def predict(self, *args):
            return [
                {
                    "surface": "Acme Labs",
                    "start": 0,
                    "end": 9,
                    "kind": "organization",
                    "score": float("nan"),
                }
            ]

    with pytest.raises(InvalidPrediction):
        await Entities(profile("offline").ner, Bad()).extract(news)


async def test_oversized_spans_fail_at_all_model_evidence_boundaries(news, now, analysis):
    from aegis.domain.models import EntityExtractionResult, EntityMention
    from aegis.entities.materialize import materialize_mentions
    from aegis.intelligence.config import profile
    from aegis.intelligence.errors import InvalidPrediction
    from aegis.intelligence.providers import Entities, Sentiment
    from aegis.intelligence.resolution import Resolver
    from aegis.intelligence.runtime import BaselineRuntime

    class Oversized:
        metadata = {}

        def predict(self, task, text, spec, labels=()):
            return [
                {
                    "surface": text,
                    "start": 0,
                    "end": len(text) + 10,
                    "kind": "organization",
                    "score": 0.8,
                }
            ]

    with pytest.raises(InvalidPrediction):
        await Entities(profile("offline").ner, Oversized()).extract(news)
    invalid = analysis.model_copy(
        update={
            "document_id": news.document_id,
            "analysis_type": "entity_extraction",
            "outputs": (
                EntityExtractionResult(
                    surface=news.text,
                    start_offset=0,
                    end_offset=len(news.text) + 10,
                    predicted_kind="organization",
                    confidence=0.8,
                ),
            ),
        }
    )
    with pytest.raises(ValueError):
        materialize_mentions(news, invalid)
    entity = Entity(
        entity_id=new_id("ent"), canonical_name="Acme Labs", kind="organization", created_at=now
    )
    mention = EntityMention(
        mention_id=new_id("mention"),
        document_id=news.document_id,
        surface=news.text,
        start_offset=0,
        end_offset=len(news.text) + 10,
        entity_id=entity.entity_id,
        evidence_kind="fact",
    )
    with pytest.raises(ValueError):
        await Resolver().resolve(news, (mention,), (entity,))
    with pytest.raises(ValueError):
        await Sentiment(profile("offline").sentiment, BaselineRuntime()).analyze_entity(
            news, entity, (mention,)
        )


def test_exact_entity_ties_remain_unresolved_with_zero_margin(now):
    from aegis.intelligence.resolution import Resolver

    a = Entity(
        entity_id=new_id("ent"), canonical_name="Acme Labs", kind="organization", created_at=now
    )
    b = a.model_copy(update={"entity_id": new_id("ent")})
    resolver = Resolver(ambiguity_margin=0)
    assert resolver.choose(resolver.rank("Acme Labs", (a, b))) == (None, 0.0)
