"""Entity registry, key-based candidate lookup and the mappings route, on PostgreSQL."""
# ruff: noqa: F811 -- pytest imports the disposable-schema fixture by name.

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from aegis.entities.registry import InstrumentSeed, register
from aegis.intelligence.pipeline import SMALL_UNIVERSE, AnalysisPipeline
from aegis.intelligence.resolution import Resolver
from aegis.persistence.models import (
    AssetMappingRow,
    DocumentRow,
    EntityMentionRow,
    EntityNameRow,
    EntityRow,
    SourceRow,
)
from aegis.settings import Settings
from apps.api.main import create_app
from tests.ingestion.test_pipeline import repository  # noqa: F401
from tests.integration.test_feed import analysis, identity, seed_doc

pytestmark = [pytest.mark.integration, pytest.mark.database]
NOW = datetime(2026, 1, 5, tzinfo=UTC)
TEXT = "Meridian Freight announced record volumes."


def seeds(*values):
    return [InstrumentSeed.model_validate(value) for value in values]


MERIDIAN = {
    "name": "Meridian Freight Limited",
    "aliases": ["MFL Logistics"],
    "listings": [
        {"identifier": "MERIDIAN", "venue": "XNSE"},
        {"identifier": "512345", "venue": "XBOM"},
        {"scheme": "isin", "identifier": "INE000A01018"},
    ],
}


def counts(session):
    return tuple(
        session.scalar(select(func.count()).select_from(table))
        for table in (EntityRow, EntityNameRow, AssetMappingRow)
    )


def test_seeding_is_idempotent_and_keeps_one_entity_for_two_venues(repository):
    with repository.sessions.begin() as session:
        report = register(session, seeds(MERIDIAN), NOW)
        assert (report.entities_created, report.mappings_created) == (1, 3)
        # Name: full and core key. Alias: one key (no legal form to drop).
        assert report.names_added == 3 and report.shared_keys == ()
        first = counts(session)
        assert first == (1, 3, 3)
    with repository.sessions.begin() as session:
        again = register(session, seeds(MERIDIAN), NOW)
        assert (again.entities_created, again.entities_existing) == (0, 1)
        assert (again.names_added, again.mappings_created, again.mappings_existing) == (0, 0, 3)
        assert counts(session) == first
        venues = session.scalars(
            select(AssetMappingRow.venue).order_by(AssetMappingRow.venue.nulls_last())
        ).all()
        assert venues == ["XBOM", "XNSE", None]


def test_seeding_reuses_an_existing_entity_and_reports_shared_keys(repository):
    existing = identity("ent", 7)
    with repository.sessions.begin() as session:
        session.add(
            EntityRow(
                entity_id=existing,
                canonical_name="Atlas Labs",
                kind="organization",
                created_at=NOW,
            )
        )
        session.flush()
        report = register(
            session,
            seeds(
                {"name": "Atlas Labs", "listings": [{"identifier": "ATLS", "venue": "XNAS"}]},
                {"name": "Atlas Labs Inc."},  # a different entity whose core is the same
            ),
            NOW,
        )
        assert (report.entities_existing, report.entities_created) == (1, 1)
        assert report.shared_keys == ("atlas labs",)
        assert session.scalar(select(AssetMappingRow.entity_id)) == existing


def test_a_listing_belongs_to_one_entity_and_the_seed_reports_what_it_skips(repository):
    with repository.sessions.begin() as session:
        register(session, seeds(MERIDIAN), NOW)
        report = register(
            session,
            seeds(
                # The same NSE listing claimed by a second entity is skipped and reported.
                {
                    "name": "Other Freight",
                    "listings": [{"identifier": "MERIDIAN", "venue": "XNSE"}],
                },
                # Meridian's file entry no longer lists the BSE code or the ISIN.
                {**MERIDIAN, "listings": [{"identifier": "MERIDIAN", "venue": "XNSE"}]},
            ),
            NOW,
        )
        owner = session.scalar(
            select(EntityRow.entity_id).where(EntityRow.canonical_name == MERIDIAN["name"])
        )
        assert report.listing_conflicts == (
            f"Other Freight: exchange_symbol:MERIDIAN@XNSE belongs to {owner}",
        )
        assert report.listings_not_in_file == (
            "Meridian Freight Limited: exchange_symbol:512345@XBOM",
            "Meridian Freight Limited: isin:INE000A01018",
        )
        # The seed only adds: the unlisted rows stay, and no second mapping was written.
        assert session.scalar(select(func.count()).select_from(AssetMappingRow)) == 3
    # The database holds the rule too, whoever writes.
    with repository.sessions() as session:
        session.add(
            AssetMappingRow(
                mapping_id="map_direct",
                entity_id=session.scalar(
                    select(EntityRow.entity_id).where(EntityRow.canonical_name == "Other Freight")
                ),
                scheme="exchange_symbol",
                identifier="MERIDIAN",
                venue="XNSE",
                created_at=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def mention_fixture(session, surface=None):
    """One document whose extraction found a single mention at the start of the text."""
    session.add(SourceRow(source_id=identity("src", 1), name="S", kind="feed", created_at=NOW))
    session.flush()
    seed_doc(session, 1, NOW)
    surface = surface or "Meridian Freight"
    analysis(
        session,
        1,
        1,
        "entity_extraction",
        NOW,
        [
            {
                "result_type": "entity_extraction",
                "surface": surface,
                "start_offset": 0,
                "end_offset": len(surface),
                "confidence": 0.9,
            }
        ],
    )
    session.add(
        EntityMentionRow(
            mention_id=identity("mention", 1),
            document_id=identity("doc", 1),
            surface=surface,
            start_offset=0,
            end_offset=len(surface),
            evidence_kind="model_output",
            analysis_id=identity("ana", 1),
        )
    )


async def test_candidates_are_found_by_key_beyond_the_old_thousand_entity_cap(repository):
    with repository.sessions.begin() as session:
        mention_fixture(session)
        # Fillers sort before the seeded entity, so the old "first 1000 by id" window
        # would never have reached it.
        session.add_all(
            EntityRow(
                entity_id=identity("ent", number),
                canonical_name=f"Filler Company {number}",
                kind="organization",
                created_at=NOW,
            )
            for number in range(1, SMALL_UNIVERSE + 6)
        )
        session.flush()
        register(session, seeds(MERIDIAN, {"name": "Meridian Bank Limited"}), NOW)
        target = session.scalar(
            select(EntityRow.entity_id).where(EntityRow.canonical_name == MERIDIAN["name"])
        )
        position = session.scalar(
            select(func.count()).select_from(EntityRow).where(EntityRow.entity_id < target)
        )
        assert position >= SMALL_UNIVERSE
        session.get(DocumentRow, identity("doc", 1)).text = TEXT
    pipeline = AnalysisPipeline(repository, None, "local")
    mentions, candidates, names = pipeline.context(identity("doc", 1), identity("ana", 1))
    assert [candidate.entity_id for candidate in candidates] == [target]
    assert names == {target: ("meridian freight", "meridian freight limited", "mfl logistics")}
    document = repository.get_document(identity("doc", 1))
    result = await Resolver().resolve(document, mentions, candidates, names)
    (output,) = result.outputs
    assert (output.entity_id, output.confidence) == (target, 1.0)
    assert result.model_version == "3"


def test_a_small_curated_set_is_still_offered_whole(repository):
    """Entities written without name keys keep resolving, as they did before keys existed."""
    with repository.sessions.begin() as session:
        mention_fixture(session)
        for number, name in ((1, "Meridian Freight"), (2, "Unrelated Works")):
            session.add(
                EntityRow(
                    entity_id=identity("ent", number),
                    canonical_name=name,
                    kind="organization",
                    created_at=NOW,
                )
            )
    _, candidates, names = AnalysisPipeline(repository, None, "local").context(
        identity("doc", 1), identity("ana", 1)
    )
    assert [c.canonical_name for c in candidates] == ["Meridian Freight", "Unrelated Works"]
    assert names == {}


def test_mappings_route_lists_filters_and_pages(repository):
    with repository.sessions.begin() as session:
        register(
            session,
            seeds(
                MERIDIAN,
                {"name": "Atlas Labs Inc.", "listings": [{"identifier": "ATLS", "venue": "XNAS"}]},
            ),
            NOW,
        )
        meridian = session.scalar(
            select(EntityRow.entity_id).where(EntityRow.canonical_name == MERIDIAN["name"])
        )
    app = create_app(Settings(_env_file=None, security_enabled=False, otel_enabled=False))
    app.state.ingestion_service = SimpleNamespace(repository=repository)
    client = TestClient(app)
    path = "/api/v1/assets/mappings"
    everything = client.get(path).json()
    assert len(everything["data"]) == 4 and not everything["pagination"]["has_more"]
    assert [m["mapping_id"] for m in everything["data"]] == sorted(
        m["mapping_id"] for m in everything["data"]
    )
    first = client.get(path, params={"limit": 3}).json()
    rest = client.get(path, params={"cursor": first["pagination"]["next_cursor"]}).json()
    assert first["pagination"]["has_more"] and len(rest["data"]) == 1
    by_venue = client.get(path, params={"venue": "XNSE"}).json()["data"]
    assert [(m["identifier"], m["entity_id"]) for m in by_venue] == [("MERIDIAN", meridian)]
    assert len(client.get(path, params={"entity_id": meridian}).json()["data"]) == 3
    isin = client.get(path, params={"scheme": "isin"}).json()["data"]
    assert [(m["identifier"], m["venue"]) for m in isin] == [("INE000A01018", None)]
    assert client.get(path, params={"venue": "XNYS"}).json()["data"] == []
    assert client.get(path, params={"as_of": "2026-01-04T00:00:00Z"}).json()["data"] == []
    assert client.get(path, params={"scheme": "ticker"}).status_code == 422
    assert UUID(everything["data"][0]["mapping_id"].removeprefix("map_"))


def test_the_stockviz_seed_file_registers_without_conflicts(repository):
    import json
    from pathlib import Path

    raw = json.loads(Path("data/instruments/stockviz.json").read_text(encoding="utf-8"))
    with repository.sessions.begin() as session:
        report = register(session, seeds(*raw), NOW)
        assert (report.entities_created, report.mappings_created) == (32, 64)
        assert report.shared_keys == () and report.listing_conflicts == ()
        again = register(session, seeds(*raw), NOW)
        assert (again.entities_created, again.mappings_created, again.mappings_existing) == (
            0,
            0,
            64,
        )
