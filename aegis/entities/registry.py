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

# ISO 10383 market identifier code, for example XNAS, XNYS, XNSE, XBOM.
MIC = re.compile(r"^[A-Z0-9]{4}$")
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
        if self.scheme == "exchange_symbol" and not (self.venue and MIC.fullmatch(self.venue)):
            raise ValueError("an exchange symbol needs a venue that is an ISO 10383 MIC code")
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
        for listing in seed.listings:
            existing = session.scalar(
                select(AssetMappingRow.mapping_id).where(
                    AssetMappingRow.entity_id == entity.entity_id,
                    AssetMappingRow.scheme == listing.scheme,
                    AssetMappingRow.identifier == listing.identifier,
                    AssetMappingRow.venue.is_not_distinct_from(listing.venue),
                )
            )
            if existing:
                counts["mappings_existing"] += 1
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
    return SeedReport(**counts, shared_keys=tuple(shared))
