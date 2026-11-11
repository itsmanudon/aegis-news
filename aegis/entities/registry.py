"""Curated entities with their match keys and instrument listings.

This is the write path for entities and asset mappings. It is a command, not a route:
the list changes rarely, and a route would be one more surface to secure.
"""

import re
from datetime import datetime
from typing import Literal, Self
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aegis.domain.models import NonEmpty
from aegis.intelligence.resolution import match_keys, normalized_name
from aegis.persistence.models import AssetMappingRow, EntityNameRow, EntityRow

# ISO 10383 operating MICs for the markets StockViz trades. Four letters alone is not
# enough: "NYSE" and "NASD" have the shape of a MIC and are not one. Add a code here,
# checked against the ISO 10383 list, when a new venue is needed.
MICS = frozenset(
    {
        "XNAS",  # Nasdaq
        "XNYS",  # New York Stock Exchange
        "XASE",  # NYSE American
        "ARCX",  # NYSE Arca
        "BATS",  # Cboe BZX
        "XNSE",  # National Stock Exchange of India
        "XBOM",  # BSE
        "XLON",  # London Stock Exchange
        "XETR",  # Xetra (Deutsche Börse)
        "XJPX",  # Japan Exchange Group, which operates the Tokyo Stock Exchange
        "XTSE",  # Toronto Stock Exchange
    }
)
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


class Listing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scheme: Literal["exchange_symbol", "isin", "provider_id"] = "exchange_symbol"
    identifier: NonEmpty
    venue: NonEmpty | None = None

    @model_validator(mode="after")
    def check_vocabulary(self) -> Self:
        if self.identifier != self.identifier.strip():
            raise ValueError("identifier must not have surrounding whitespace")
        if self.scheme == "exchange_symbol" and self.venue not in MICS:
            raise ValueError(
                "an exchange symbol needs a venue from the MIC allow-list: "
                + ", ".join(sorted(MICS))
            )
        if self.scheme == "isin" and not (ISIN.fullmatch(self.identifier) and self.venue is None):
            raise ValueError("an ISIN is twelve characters and has no venue")
        return self


class InstrumentSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: NonEmpty
    kind: Literal["organization", "person", "location", "other"] = "organization"
    aliases: tuple[NonEmpty, ...] = ()
    listings: tuple[Listing, ...] = ()

    @model_validator(mode="after")
    def check_name(self) -> Self:
        if not normalized_name(self.name):
            raise ValueError("name must contain letters or digits")
        return self


class SeedReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    entities_created: int = 0
    entities_existing: int = 0
    names_added: int = 0
    mappings_created: int = 0
    mappings_existing: int = 0
    # Keys that now lead to more than one entity. A mention that matches such a key is
    # left unresolved, so each one is a name worth disambiguating with an alias.
    shared_keys: tuple[str, ...] = Field(default=())
    # Listings the file gives to one entity that already belong to another. Each was
    # skipped; a listing maps to one entity only.
    listing_conflicts: tuple[str, ...] = Field(default=())
    # Listings stored for an entity in the file that the file no longer lists. The seed
    # only adds, so these stay until removed by hand.
    listings_not_in_file: tuple[str, ...] = Field(default=())


def describe(scheme: str, identifier: str, venue: str | None) -> str:
    return f"{scheme}:{identifier}@{venue}" if venue else f"{scheme}:{identifier}"


def stable(prefix: str, identity: str) -> str:
    return f"{prefix}_{uuid5(NAMESPACE_URL, identity)}"


def find_entity(session: Session, seed: InstrumentSeed) -> EntityRow | None:
    """An entity already registered under this name's key, or stored with this exact name."""
    full = normalized_name(seed.name)
    entity_id = session.scalar(
        select(EntityNameRow.entity_id)
        .where(EntityNameRow.key == full, EntityNameRow.kind == "name")
        .order_by(EntityNameRow.entity_id)
        .limit(1)
    )
    if entity_id:
        return session.get(EntityRow, entity_id)
    return session.scalar(
        select(EntityRow)
        .where(EntityRow.canonical_name == seed.name)
        .order_by(EntityRow.entity_id)
        .limit(1)
    )


def register(session: Session, seeds: list[InstrumentSeed], now: datetime) -> SeedReport:
    """Upsert entities, name keys and mappings. Running it again changes nothing."""
    counts = dict.fromkeys(
        (
            "entities_created",
            "entities_existing",
            "names_added",
            "mappings_created",
            "mappings_existing",
        ),
        0,
    )
    touched: set[str] = set()
    conflicts: list[str] = []
    stale: list[str] = []
    for seed in seeds:
        entity = find_entity(session, seed)
        if entity is None:
            entity = EntityRow(
                entity_id=stable("ent", "instrument:" + normalized_name(seed.name)),
                canonical_name=seed.name,
                kind=seed.kind,
                created_at=now,
            )
            session.add(entity)
            session.flush()
            counts["entities_created"] += 1
        else:
            counts["entities_existing"] += 1
        names = [(key, "name") for key in match_keys(seed.name)]
        names += [(key, "alias") for alias in seed.aliases for key in match_keys(alias)]
        for key, kind in names:
            touched.add(key)
            if session.get(EntityNameRow, (entity.entity_id, key)) is None:
                session.add(
                    EntityNameRow(entity_id=entity.entity_id, key=key, kind=kind, created_at=now)
                )
                session.flush()
                counts["names_added"] += 1
        listed = {(item.scheme, item.identifier, item.venue) for item in seed.listings}
        for scheme, identifier, venue in session.execute(
            select(AssetMappingRow.scheme, AssetMappingRow.identifier, AssetMappingRow.venue)
            .where(AssetMappingRow.entity_id == entity.entity_id)
            .order_by(AssetMappingRow.scheme, AssetMappingRow.identifier, AssetMappingRow.venue)
        ):
            if (scheme, identifier, venue) not in listed:
                stale.append(f"{seed.name}: {describe(scheme, identifier, venue)}")
        for listing in seed.listings:
            owner = session.scalar(
                select(AssetMappingRow.entity_id).where(
                    AssetMappingRow.scheme == listing.scheme,
                    AssetMappingRow.identifier == listing.identifier,
                    AssetMappingRow.venue.is_not_distinct_from(listing.venue),
                )
            )
            if owner == entity.entity_id:
                counts["mappings_existing"] += 1
                continue
            if owner is not None:
                label = describe(listing.scheme, listing.identifier, listing.venue)
                conflicts.append(f"{seed.name}: {label} belongs to {owner}")
                continue
            identity = "|".join(
                (entity.entity_id, listing.scheme, listing.identifier, listing.venue or "")
            )
            session.add(
                AssetMappingRow(
                    mapping_id=stable("map", identity),
                    entity_id=entity.entity_id,
                    scheme=listing.scheme,
                    identifier=listing.identifier,
                    venue=listing.venue,
                    created_at=now,
                )
            )
            session.flush()
            counts["mappings_created"] += 1
    shared = (
        session.scalars(
            select(EntityNameRow.key)
            .where(EntityNameRow.key.in_(touched))
            .group_by(EntityNameRow.key)
            .having(func.count() > 1)
            .order_by(EntityNameRow.key)
        ).all()
        if touched
        else []
    )
    return SeedReport(
        **counts,
        shared_keys=tuple(shared),
        listing_conflicts=tuple(conflicts),
        listings_not_in_file=tuple(stale),
    )
