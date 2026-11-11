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
