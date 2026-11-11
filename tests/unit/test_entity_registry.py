"""Match keys, seed validation and name-aware ranking. Database behaviour is covered in
tests/integration/test_instruments.py."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from aegis.domain.models import Entity
from aegis.entities.registry import InstrumentSeed, Listing
from aegis.intelligence.resolution import Resolver, match_keys


def entity(number, name):
    return Entity(
        entity_id=f"ent_{UUID(int=number)}",
        canonical_name=name,
        kind="organization",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("name", "keys"),
    [
        ("Apple Inc.", ("apple inc", "apple")),
        ("The Coca-Cola Company", ("the coca cola company", "coca cola")),
        ("Reliance Industries Limited", ("reliance industries limited", "reliance industries")),
        ("Tata Motors Pvt. Ltd.", ("tata motors pvt ltd", "tata motors")),
        ("Meridian Holdings", ("meridian holdings",)),  # not a legal form: kept
        ("Limited", ("limited",)),  # never reduced to nothing
        ("  ÅLAND   Shipping AB ", ("åland shipping ab", "åland shipping")),
        ("!!!", ()),
    ],
)
def test_match_keys(name, keys):
    assert match_keys(name) == keys


def test_a_name_matches_its_core_and_stored_aliases():
    apple, other = entity(1, "Apple Inc."), entity(2, "Applied Materials, Inc.")
    resolver = Resolver()
    assert resolver.choose(resolver.rank("Apple", (apple, other))) == (apple.entity_id, 1.0)
    # A stored alias is supplied per call by whoever looked the candidates up.
    ranks = resolver.rank("Big Blue", (apple, other), {other.entity_id: ("big blue",)})
    assert resolver.choose(ranks) == (other.entity_id, 1.0)
    assert resolver.choose(resolver.rank("Big Blue", (apple, other))) == (None, 0.0)


def test_a_key_shared_by_two_entities_stays_unresolved():
    first, second = entity(1, "Meridian Ltd"), entity(2, "Meridian Inc")
    resolver = Resolver()
    assert resolver.choose(resolver.rank("Meridian", (first, second))) == (None, 0.0)


@pytest.mark.parametrize(
    "listing",
    [
        {"identifier": "AAPL"},  # an exchange symbol needs a venue
        {"identifier": "AAPL", "venue": "NASDAQ"},  # a name, not a MIC code
        {"identifier": "AAPL", "venue": "NASD"},  # MIC-shaped, and not a MIC code
        {"identifier": "IBM", "venue": "NYSE"},
        {"identifier": "AAPL", "venue": "xnas"},
        {"identifier": " AAPL", "venue": "XNAS"},
        {"scheme": "isin", "identifier": "US0378331005", "venue": "XNAS"},
        {"scheme": "isin", "identifier": "0378331005"},
        {"identifier": "AAPL", "venue": "XNAS", "currency": "USD"},
    ],
)
def test_listings_outside_the_vocabulary_are_rejected(listing):
    with pytest.raises(ValidationError):
        Listing.model_validate(listing)


def test_valid_seed_shapes():
    seed = InstrumentSeed.model_validate(
        {
            "name": "Example Industries Limited",
            "aliases": ["Example Industries"],
            "listings": [
                {"identifier": "EXAMPLE", "venue": "XNSE"},
                {"identifier": "500000", "venue": "XBOM"},
                {"scheme": "isin", "identifier": "INE000A01018"},
            ],
        }
    )
    assert [listing.scheme for listing in seed.listings] == ["exchange_symbol"] * 2 + ["isin"]
    assert seed.kind == "organization"
    with pytest.raises(ValidationError):
        InstrumentSeed.model_validate({"name": "???"})


# Disambiguation cases (audit AG-6). Each line: surface, the kind the extractor predicted,
# candidate name, stored aliases, and whether the mention should resolve.
DISAMBIGUATION = [
    ("Apple", "organization", "Apple Inc.", (), True),
    ("Apple", None, "Apple Inc.", (), True),
    ("Apple", "other", "Apple Inc.", (), True),  # the offline extractor's label for any span
    ("Apple", "person", "Apple Inc.", (), False),
    ("Jordan", "location", "Jordan Group Ltd", (), False),
    ("SAP", "organization", "SAP SE", (), True),
    ("Sap", None, "SAP SE", (), False),  # short: only as written
    ("Visa", None, "Visa Inc.", (), True),
    ("VISA", None, "Visa Inc.", (), False),
    ("Amazon", None, "Amazon.com, Inc.", (), False),  # needs an alias
    ("Amazon", None, "Amazon.com, Inc.", ("Amazon",), True),
    ("Google", None, "Alphabet Inc.", ("Google",), True),
    ("Disney", None, "The Walt Disney Company", ("Disney",), True),
    ("Reliance Industries", "organization", "Reliance Industries Limited", (), True),
]


@pytest.mark.parametrize(("surface", "kind", "name", "aliases", "resolves"), DISAMBIGUATION)
def test_disambiguation_cases(surface, kind, name, aliases, resolves):
    target, other = entity(1, name), entity(2, "Unrelated Holdings")
    resolver = Resolver()
    names = {target.entity_id: aliases} if aliases else {}
    chosen, _ = resolver.choose(resolver.rank(surface, (target, other), names, kind))
    assert (chosen == target.entity_id) is resolves


async def test_resolve_uses_the_kind_the_extraction_predicted():
    from aegis.domain.models import EntityMention, NewsDocument

    now = datetime(2026, 1, 1, tzinfo=UTC)
    document = NewsDocument(
        document_id=f"doc_{UUID(int=9)}",
        ingestion_id=f"ing_{UUID(int=9)}",
        source_id=f"src_{UUID(int=9)}",
        title="Synthetic",
        text="Apple met Apple.",
        first_seen_at=now,
        ingested_at=now,
        created_at=now,
    )
    mentions = tuple(
        EntityMention(
            mention_id=f"mention_{UUID(int=n)}",
            document_id=document.document_id,
            surface="Apple",
            start_offset=start,
            end_offset=start + 5,
            evidence_kind="model_output",
            analysis_id=f"ana_{UUID(int=1)}",
        )
        for n, start in ((1, 0), (2, 10))
    )
    apple = entity(1, "Apple Inc.")
    result = await Resolver().resolve(
        document, mentions, (apple,), kinds={mentions[0].mention_id: "person"}
    )
    assert [o.entity_id for o in result.outputs] == [None, apple.entity_id]
    assert result.model_version == "3"
