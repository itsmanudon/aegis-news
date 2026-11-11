"""Incremental document feed: signed documents in the order they were last signed.

The position of a document is (signed_xid, document_id): the id of the transaction that
signed it last. A row is returned only once every older transaction has finished, so a
transaction that commits late holds the feed back instead of being skipped, whatever the
clocks say. A document enters the feed when its first run is signed and moves forward when
a later run is signed, so a consumer that keeps the resume cursor sees each change once.
Each bundle describes the latest signed run only, so a consumer replaces what it holds.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from pydantic import TypeAdapter
from sqlalchemy import select, text, tuple_
from sqlalchemy.orm import Session

from aegis.contracts.feed import (
    FeedDocument,
    FeedEntity,
    FeedEvent,
    FeedInstrument,
    FeedItem,
    FeedManifest,
)
from aegis.domain.ids import DocumentId
from aegis.domain.models import AnalysisResult, EntityResolutionResult, EventExtractionResult
from aegis.ingestion.repository import source_value
from aegis.intelligence.persistence import from_row
from aegis.intelligence.pipeline import stable_id
from aegis.intelligence.read_models import fingerprint, pack, unpack
from aegis.persistence.models import (
    AnalysisRow,
    AssetMappingRow,
    Base,
    DocumentRow,
    EntityRow,
    IngestionRow,
    NewsEventRow,
    SourceRow,
    finished_below,
)

Position = tuple[int, str]

START: Position = (-1, "")
# Analyses a consumer stores. Extraction outputs quote the article and embeddings are
# large, so neither is returned; event extraction only supplies each event's type.
FEED_ANALYSES = ("topic", "sentiment", "entity_resolution")
CURSOR_MAXIMUM = 4096


def encode_position(position: Position, filters: dict[str, Any]) -> str:
    return pack(
        {
            "v": 2,
            "kind": "feed",
            "filters": fingerprint(filters),
            "key": [position[0], position[1]],
        }
    )


def decode_position(value: str, filters: dict[str, Any]) -> Position:
    data = unpack(value, CURSOR_MAXIMUM)
    if not isinstance(data, dict) or set(data) != {"v", "kind", "filters", "key"}:
        raise ValueError("invalid feed cursor")
    if (
        type(data["v"]) is not int
        or data["v"] != 2
        or data["kind"] != "feed"
        or data["filters"] != fingerprint(filters)
    ):
        raise ValueError("feed cursor filter mismatch")
    key = data["key"]
    if (
        not isinstance(key, list)
        or len(key) != 2
        or type(key[0]) is not int
        or key[0] < -1
        or not isinstance(key[1], str)
    ):
        raise ValueError("invalid feed cursor key")
    if key[1]:
        TypeAdapter(DocumentId).validate_python(key[1])
    return key[0], key[1]


def linked_to_instrument(bound: datetime, listing: dict[str, str]) -> Any:
    """Documents with an entity resolution that leads to a matching asset mapping.

    ``listing`` narrows the mapping by scheme, venue or identifier; empty means any.
    """
    clauses = "".join(f" AND m.{column} = :listing_{column}" for column in listing)
    return text(
        """EXISTS (
          SELECT 1 FROM analyses a
          CROSS JOIN LATERAL jsonb_array_elements(a.outputs) o
          JOIN asset_mappings m ON m.entity_id = o->>'entity_id'
          WHERE a.document_id = documents.document_id
            AND a.analysis_type = 'entity_resolution'
            AND a.available_at <= :listing_bound AND m.created_at <= :listing_bound"""
        + clauses
        + ")"
    ).bindparams(listing_bound=bound, **{f"listing_{k}": v for k, v in listing.items()})


def read(
    session: Session,
    after: Position,
    bound: datetime,
    limit: int,
    listing: dict[str, str] | None = None,
    since: datetime | None = None,
) -> tuple[list[FeedItem], bool, Position]:
    """Up to ``limit`` bundles after ``after``, whether more exist, and where to resume.

    ``bound`` is the point in time for analyses, events and mappings. ``since`` keeps only
    documents last signed at or after it.

    With ``listing`` given, even empty, only documents linked to an instrument are
    returned; its keys (scheme, venue, identifier) narrow which instrument.
    """
    query = (
        select(DocumentRow, IngestionRow.source_url)
        .join(IngestionRow, IngestionRow.ingestion_id == DocumentRow.ingestion_id)
        .where(
            DocumentRow.signed_xid.is_not(None),
            # Only transactions that have ended: a running one may still commit below.
            DocumentRow.signed_xid < finished_below(),
            tuple_(DocumentRow.signed_xid, DocumentRow.document_id) > tuple_(*after),
        )
        .order_by(DocumentRow.signed_xid, DocumentRow.document_id)
        .limit(limit + 1)
    )
    if listing is not None:
        query = query.where(linked_to_instrument(bound, listing))
    if since is not None:
        query = query.where(DocumentRow.last_signed_at >= since)
    rows = session.execute(query).all()
    more = len(rows) > limit
    rows = rows[:limit]
    if not rows:
        return [], False, after
    resume: Position = (cast(int, rows[-1][0].signed_xid), rows[-1][0].document_id)
    documents = [row[0] for row in rows]
    ids = [document.document_id for document in documents]

    sources = {
        row.source_id: source_value(row)
        for row in session.scalars(
            select(SourceRow).where(
                SourceRow.source_id.in_({document.source_id for document in documents})
            )
        )
    }

    # A bundle is the document as of its latest signed run: only the analyses that run
    # signed, and the events and instrument links that follow from them. Analyses from
    # earlier runs, or not yet signed, are left out.
    manifests: dict[str, list[FeedManifest]] = defaultdict(list)
    current: dict[str, set[str]] = defaultdict(set)
    for signed in session.execute(
        text(
            """
            SELECT r->>'subject_id' AS document_id, s.manifest_hash, s.key_id, s.created_at,
                   s.manifest->'records' AS records
            FROM signed_manifests s
            CROSS JOIN LATERAL jsonb_array_elements(s.manifest->'records') r
            WHERE s.created_at >= :earliest AND s.created_at <= :bound
              AND r->>'operation' = 'normalization'
              AND r->>'subject_id' = ANY(:ids)
            ORDER BY s.created_at, s.manifest_hash
            """
        ),
        {
            "ids": ids,
            "bound": bound,
            # A manifest cannot predate the first sight of any document it covers.
            "earliest": min(document.first_seen_at for document in documents),
        },
    ).mappings():
        # Rows arrive oldest first, so the last one per document is its latest run.
        current[signed["document_id"]] = {
            record["subject_id"]
            for record in signed["records"]
            if record["operation"] == "analysis"
        }
        manifests[signed["document_id"]].append(
            FeedManifest(
                manifest_hash=signed["manifest_hash"],
                key_id=signed["key_id"],
                signed_at=signed["created_at"],
            )
        )

    analyses: dict[str, list[AnalysisResult]] = defaultdict(list)
    # document -> entity -> (confidence, resolving analysis)
    resolved: dict[str, dict[str, tuple[float, str]]] = defaultdict(dict)
    event_types: dict[str, tuple[str, float]] = {}
    for analysis_row in session.scalars(
        select(AnalysisRow)
        .where(
            AnalysisRow.document_id.in_(ids),
            AnalysisRow.analysis_type.in_((*FEED_ANALYSES, "event_extraction")),
            AnalysisRow.available_at <= bound,
        )
        .order_by(AnalysisRow.available_at, AnalysisRow.analysis_id)
    ):
        if analysis_row.analysis_id not in current[analysis_row.document_id]:
            continue
        value = from_row(analysis_row)
        if value.analysis_type in FEED_ANALYSES:
            analyses[value.document_id].append(value)
        for index, output in enumerate(value.outputs):
            if isinstance(output, EventExtractionResult):
                # The pipeline derives an event's identity from its analysis and position.
                event_types[stable_id("evt", f"{value.analysis_id}:{index}")] = (
                    output.proposed_event_type,
                    output.confidence,
                )
            elif isinstance(output, EntityResolutionResult) and output.entity_id:
                best = resolved[value.document_id].get(output.entity_id)
                if best is None or output.confidence >= best[0]:
                    resolved[value.document_id][output.entity_id] = (
                        output.confidence,
                        value.analysis_id,
                    )

    mappings: dict[str, list[tuple[EntityRow, AssetMappingRow]]] = defaultdict(list)
    entity_ids = {entity for links in resolved.values() for entity in links}
    entities = (
        {
            row.entity_id: row
            for row in session.scalars(select(EntityRow).where(EntityRow.entity_id.in_(entity_ids)))
        }
        if entity_ids
        else {}
    )
    if entity_ids:
        for entity, mapping in session.execute(
            select(EntityRow, AssetMappingRow)
            .join(AssetMappingRow, AssetMappingRow.entity_id == EntityRow.entity_id)
            .where(EntityRow.entity_id.in_(entity_ids), AssetMappingRow.created_at <= bound)
            .order_by(AssetMappingRow.mapping_id)
        ):
            mappings[entity.entity_id].append((entity, mapping))

    events: dict[str, list[FeedEvent]] = defaultdict(list)
    links = Base.metadata.tables["event_documents"]
    for linked in session.execute(
        select(NewsEventRow, links.c.document_id)
        .join(
            links,
            (links.c.event_id == NewsEventRow.event_id)
            & (links.c.revision == NewsEventRow.revision),
        )
        .where(links.c.document_id.in_(ids), NewsEventRow.available_at <= bound)
        .order_by(NewsEventRow.available_at, NewsEventRow.event_id, NewsEventRow.revision)
    ):
        event = cast(NewsEventRow, linked[0])
        # A fact event has no analysis and stands on its own.
        if event.analysis_id and event.analysis_id not in current[cast(str, linked[1])]:
            continue
        extraction = event_types.get(event.event_id)
        events[cast(str, linked[1])].append(
            FeedEvent(
                event_id=event.event_id,
                revision=event.revision,
                event_type=extraction[0] if extraction else None,
                confidence=extraction[1] if extraction else None,
                occurred_at=event.occurred_at,
                created_at=event.created_at,
                available_at=event.available_at,
                evidence_kind=event.evidence_kind,
                analysis_id=event.analysis_id,
            )
        )

    items = []
    for document, source_url in rows:
        instruments = [
            FeedInstrument(
                entity_id=entity.entity_id,
                canonical_name=entity.canonical_name,
                kind=entity.kind,
                mapping_id=mapping.mapping_id,
                scheme=mapping.scheme,
                identifier=mapping.identifier,
                venue=mapping.venue,
                resolution_analysis_id=analysis_id,
                confidence=confidence,
            )
            for entity_id, (confidence, analysis_id) in sorted(
                resolved[document.document_id].items()
            )
            for entity, mapping in mappings.get(entity_id, ())
        ]
        items.append(
            FeedItem(
                document=FeedDocument(
                    document_id=document.document_id,
                    ingestion_id=document.ingestion_id,
                    source_id=document.source_id,
                    title=document.title,
                    url=source_url,
                    language=document.language,
                    published_at=document.published_at,
                    first_seen_at=document.first_seen_at,
                    ingested_at=document.ingested_at,
                    created_at=document.created_at,
                    available_at=document.available_at,
                    last_signed_at=document.last_signed_at,
                    revision=document.revision,
                ),
                source=sources[document.source_id],
                analyses=tuple(analyses[document.document_id]),
                entities=tuple(
                    FeedEntity(
                        entity_id=entity_id,
                        canonical_name=entities[entity_id].canonical_name,
                        kind=entities[entity_id].kind,
                        resolution_analysis_id=analysis_id,
                        confidence=confidence,
                    )
                    for entity_id, (confidence, analysis_id) in sorted(
                        resolved[document.document_id].items()
                    )
                    if entity_id in entities
                ),
                instruments=tuple(instruments),
                events=tuple(events[document.document_id]),
                manifests=tuple(manifests[document.document_id]),
            )
        )
    return items, more, resume
