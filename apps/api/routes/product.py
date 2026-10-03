"""Product read models assembled from canonical records; no inferred facts."""

import asyncio
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import select, text, true
from sqlalchemy.orm import Session

from aegis.contracts.api import (
    CollectionResponse,
    CursorPagination,
    ErrorCode,
    ResponseMeta,
    SingleResponse,
)
from aegis.domain.models import (
    AnalysisResult,
    Entity,
    EntityMention,
    EntityResolutionResult,
    MediaAsset,
    NewsDocument,
    NewsEvent,
    ProvenanceRecord,
    Source,
)
from aegis.ingestion.repository import document_value, object_value, source_value
from aegis.intelligence.persistence import from_row
from aegis.intelligence.pipeline import AnalysisPipeline, event_value, record
from aegis.persistence.models import (
    AnalysisRow,
    DocumentMediaLinkRow,
    DocumentRow,
    EntityMentionRow,
    EntityRow,
    MediaAssetRow,
    NewsEventRow,
    ProvenanceRow,
    RawObjectRow,
    SourceRow,
)
from aegis.provenance.service import ProvenanceService, VerificationResult
from aegis.security.auth import product_access
from apps.api.errors import ApiException
from apps.api.routes.ingestions import repository

router = APIRouter(tags=["product"])
Limit = Annotated[int, Query(ge=1, le=100)]
Cutoff = Annotated[AwareDatetime | None, Query()]
Cursor = Annotated[str | None, Query(max_length=128)]


class DocumentIntelligence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document: NewsDocument
    source: Source
    analyses: tuple[AnalysisResult, ...]
    mentions: tuple[EntityMention, ...]
    entities: tuple[Entity, ...]
    events: tuple[NewsEvent, ...]
    media: tuple[MediaAsset, ...]
    provenance: tuple[ProvenanceRecord, ...]


class SimilarDocument(BaseModel):
    document: NewsDocument
    distance: float
    model_name: str


def meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def page[T](values: list[T], limit: int, request: Request, key: Any) -> CollectionResponse[T]:
    more = len(values) > limit
    return CollectionResponse(
        data=tuple(values[:limit]),
        pagination=CursorPagination(
            has_more=more,
            next_cursor=key(values[limit - 1]) if more else None,
        ),
        meta=meta(request),
    )


def visible_document(session: Session, document_id: str, cutoff: datetime | None) -> NewsDocument:
    row = session.get(DocumentRow, document_id)
    if row is None or (cutoff and row.created_at > cutoff):
        raise ApiException(ErrorCode.NOT_FOUND, "Document not found at this cutoff", 404)
    return document_value(row)


def resolved_documents(entity_id: str) -> Any:
    return select(AnalysisRow.document_id).where(
        AnalysisRow.analysis_type == "entity_resolution",
        AnalysisRow.outputs.contains([{"entity_id": entity_id}]),
    )


@router.get(
    "/documents",
    response_model=CollectionResponse[NewsDocument],
    dependencies=[product_access("documents:read")],
)
@router.get(
    "/search",
    response_model=CollectionResponse[NewsDocument],
    dependencies=[product_access("documents:read")],
)
def documents(
    request: Request,
    limit: Limit = 25,
    cursor: Cursor = None,
    as_of: Cutoff = None,
    q: str = "",
    source_id: str | None = None,
    entity_id: str | None = None,
) -> CollectionResponse[NewsDocument]:
    query = select(DocumentRow).order_by(DocumentRow.document_id).limit(limit + 1)
    if cursor:
        query = query.where(DocumentRow.document_id > cursor)
    if as_of:
        query = query.where(DocumentRow.created_at <= as_of)
    if q:
        # Literal substring matching, with pg_trgm available for indexed deployments.
        query = query.where(
            DocumentRow.title.icontains(q, autoescape=True)
            | DocumentRow.text.icontains(q, autoescape=True)
        )
    if source_id:
        query = query.where(DocumentRow.source_id == source_id)
    if entity_id:
        ids = resolved_documents(entity_id)
        if as_of:
            ids = ids.where(AnalysisRow.available_at <= as_of)
        query = query.where(DocumentRow.document_id.in_(ids))
    with repository(request).sessions() as session:
        return page(
            [document_value(row) for row in session.scalars(query)],
            limit,
            request,
            lambda v: v.document_id,
        )


@router.get(
    "/documents/{document_id}/intelligence",
    response_model=SingleResponse[DocumentIntelligence],
    dependencies=[product_access("documents:read")],
)
def intelligence(
    document_id: str, request: Request, as_of: Cutoff = None
) -> SingleResponse[DocumentIntelligence]:
    with repository(request).sessions() as session:
        document = visible_document(session, document_id, as_of)
        source = session.get(SourceRow, document.source_id)
        assert source is not None
        query = (
            select(AnalysisRow)
            .where(AnalysisRow.document_id == document_id)
            .order_by(AnalysisRow.available_at, AnalysisRow.analysis_id)
        )
        if as_of:
            query = query.where(AnalysisRow.available_at <= as_of)
        analyses = tuple(from_row(row) for row in session.scalars(query))
        ids = [value.analysis_id for value in analyses]
        entity_ids = {
            str(output.entity_id)
            for value in analyses
            if value.analysis_type == "entity_resolution"
            for output in value.outputs
            if isinstance(output, EntityResolutionResult) and output.entity_id
        }
        entities = tuple(
            record(Entity, row)
            for row in session.scalars(
                select(EntityRow)
                .where(EntityRow.entity_id.in_(entity_ids))
                .order_by(EntityRow.entity_id)
            )
        )
        mentions = tuple(
            record(EntityMention, row)
            for row in session.scalars(
                select(EntityMentionRow).where(EntityMentionRow.analysis_id.in_(ids))
            )
        )
        events = tuple(
            event_value(session, row)
            for row in session.scalars(
                select(NewsEventRow).where(
                    NewsEventRow.analysis_id.in_(ids),
                    NewsEventRow.available_at <= as_of if as_of else true(),
                )
            )
        )
        media = []
        for row in session.scalars(
            select(MediaAssetRow)
            .join(DocumentMediaLinkRow, DocumentMediaLinkRow.media_id == MediaAssetRow.media_id)
            .where(
                DocumentMediaLinkRow.document_id == document_id,
                MediaAssetRow.created_at <= as_of if as_of else true(),
            )
        ):
            raw = session.get(RawObjectRow, row.raw_object_id)
            assert raw is not None
            media.append(
                MediaAsset(
                    media_id=row.media_id,
                    ingestion_id=row.ingestion_id,
                    kind=row.kind,
                    object=object_value(raw),
                    created_at=row.created_at,
                )
            )
        provenance_query = (
            select(ProvenanceRow)
            .where((ProvenanceRow.subject_id == document_id) | ProvenanceRow.analysis_id.in_(ids))
            .order_by(ProvenanceRow.recorded_at, ProvenanceRow.provenance_id)
        )
        if as_of:
            provenance_query = provenance_query.where(ProvenanceRow.recorded_at <= as_of)
        provenance = tuple(
            record(ProvenanceRecord, row) for row in session.scalars(provenance_query)
        )
        return SingleResponse(
            data=DocumentIntelligence(
                document=document,
                source=source_value(source),
                analyses=analyses,
                mentions=mentions,
                entities=entities,
                events=events,
                media=tuple(media),
                provenance=provenance,
            ),
            meta=meta(request),
        )


@router.get(
    "/sources",
    response_model=CollectionResponse[Source],
    dependencies=[product_access("sources:read")],
)
def sources(
    request: Request, limit: Limit = 25, cursor: Cursor = None
) -> CollectionResponse[Source]:
    query = select(SourceRow).order_by(SourceRow.source_id).limit(limit + 1)
    if cursor:
        query = query.where(SourceRow.source_id > cursor)
    with repository(request).sessions() as session:
        return page(
            [source_value(row) for row in session.scalars(query)],
            limit,
            request,
            lambda v: v.source_id,
        )


@router.get(
    "/entities",
    response_model=CollectionResponse[Entity],
    dependencies=[product_access("documents:read")],
)
def entities(
    request: Request, limit: Limit = 25, cursor: Cursor = None, as_of: Cutoff = None
) -> CollectionResponse[Entity]:
    query = select(EntityRow).order_by(EntityRow.entity_id).limit(limit + 1)
    if cursor:
        query = query.where(EntityRow.entity_id > cursor)
    if as_of:
        query = query.where(EntityRow.created_at <= as_of)
    with repository(request).sessions() as session:
        return page(
            [record(Entity, row) for row in session.scalars(query)],
            limit,
            request,
            lambda v: v.entity_id,
        )


@router.get(
    "/entities/{entity_id}",
    response_model=SingleResponse[Entity],
    dependencies=[product_access("documents:read")],
)
def entity(entity_id: str, request: Request) -> SingleResponse[Entity]:
    with repository(request).sessions() as session:
        row = session.get(EntityRow, entity_id)
        if row is None:
            raise ApiException(ErrorCode.NOT_FOUND, "Entity not found", 404)
        return SingleResponse(data=record(Entity, row), meta=meta(request))


@router.get(
    "/entities/{entity_id}/documents",
    response_model=CollectionResponse[NewsDocument],
    dependencies=[product_access("documents:read")],
)
def entity_documents(
    entity_id: str, request: Request, limit: Limit = 25, cursor: Cursor = None, as_of: Cutoff = None
) -> CollectionResponse[NewsDocument]:
    return documents(request, limit, cursor, as_of, entity_id=entity_id)


@router.get(
    "/events",
    response_model=CollectionResponse[NewsEvent],
    dependencies=[product_access("events:read")],
)
def events(
    request: Request, limit: Limit = 25, cursor: Cursor = None, as_of: Cutoff = None
) -> CollectionResponse[NewsEvent]:
    query = (
        select(NewsEventRow).order_by(NewsEventRow.event_id, NewsEventRow.revision).limit(limit + 1)
    )
    if cursor:
        try:
            identity, revision = cursor.rsplit(":", 1)
            query = query.where(
                (NewsEventRow.event_id > identity)
                | ((NewsEventRow.event_id == identity) & (NewsEventRow.revision > int(revision)))
            )
        except ValueError:
            raise ApiException(ErrorCode.INVALID_ARGUMENT, "Invalid event cursor", 422) from None
    if as_of:
        query = query.where(NewsEventRow.available_at <= as_of)
    with repository(request).sessions() as session:
        return page(
            [event_value(session, row) for row in session.scalars(query)],
            limit,
            request,
            lambda v: f"{v.event_id}:{v.revision}",
        )


@router.get(
    "/events/{event_id}",
    response_model=SingleResponse[NewsEvent],
    dependencies=[product_access("events:read")],
)
def event(
    event_id: str,
    request: Request,
    as_of: Cutoff = None,
    revision: Annotated[int | None, Query(ge=1)] = None,
) -> SingleResponse[NewsEvent]:
    query = (
        select(NewsEventRow)
        .where(NewsEventRow.event_id == event_id)
        .order_by(NewsEventRow.revision.desc())
        .limit(1)
    )
    if as_of:
        query = query.where(NewsEventRow.available_at <= as_of)
    if revision:
        query = query.where(NewsEventRow.revision == revision)
    with repository(request).sessions() as session:
        row = session.scalar(query)
        if row is None:
            raise ApiException(ErrorCode.NOT_FOUND, "Event not found at this revision/cutoff", 404)
        return SingleResponse(data=event_value(session, row), meta=meta(request))


@router.get(
    "/documents/{document_id}/similar",
    response_model=CollectionResponse[SimilarDocument],
    dependencies=[product_access("documents:read")],
)
def similar(
    document_id: str, request: Request, limit: Limit = 10, as_of: Cutoff = None
) -> CollectionResponse[SimilarDocument]:
    with repository(request).sessions() as session:
        visible_document(session, document_id, as_of)
        rows = session.execute(
            text("""
            WITH vectors AS (
              SELECT DISTINCT ON (document_id) document_id, model_name, model_version,
                provider, configuration_hash, (outputs->0->'values')::text::vector AS embedding
              FROM analyses WHERE analysis_type='embedding'
                AND (CAST(:cutoff AS timestamptz) IS NULL OR available_at <= :cutoff)
              ORDER BY document_id, available_at DESC, analysis_id DESC
            )
            SELECT b.document_id, b.model_name, b.embedding <=> a.embedding AS distance
            FROM vectors a JOIN vectors b ON a.model_name=b.model_name
              AND a.model_version=b.model_version
              AND a.provider=b.provider AND a.configuration_hash=b.configuration_hash
            JOIN documents d ON d.document_id=b.document_id
            WHERE a.document_id=:id AND b.document_id<>:id
              AND vector_norm(a.embedding)>0 AND vector_norm(b.embedding)>0
              AND (CAST(:cutoff AS timestamptz) IS NULL OR d.created_at <= :cutoff)
            ORDER BY distance, b.document_id LIMIT :limit
        """),
            {"id": document_id, "limit": limit, "cutoff": as_of},
        ).mappings()
        values = [
            SimilarDocument(
                document=visible_document(session, row["document_id"], as_of),
                distance=row["distance"],
                model_name=row["model_name"],
            )
            for row in rows
        ]
        return CollectionResponse(
            data=tuple(values), pagination=CursorPagination(), meta=meta(request)
        )


@router.post(
    "/documents/{document_id}/verify",
    response_model=SingleResponse[VerificationResult],
    dependencies=[product_access("security:verify")],
)
async def verify(document_id: str, request: Request) -> SingleResponse[VerificationResult]:
    repo = repository(request)
    pipeline = AnalysisPipeline(
        repo,
        ProvenanceService(request.app.state.provenance.crypto),
        request.app.state.settings.provenance_key_id,
    )
    try:
        result = await pipeline.verify_document(
            document_id, request.app.state.ingestion_service.storage
        )
    except LookupError:
        raise ApiException(
            ErrorCode.NOT_FOUND, "Signed document provenance is unavailable", 404
        ) from None
    for action, valid in (
        ("integrity_verification", result.valid),
        ("signature_verification", result.signature_valid),
    ):
        principal = getattr(request.state, "principal", None)
        await asyncio.to_thread(
            request.app.state.audit.emit,
            action,
            subject=document_id,
            actor=principal.subject if principal else None,
            request_id=request.state.request_id,
            outcome="success" if valid else "failure",
        )
    return SingleResponse(data=result, meta=meta(request))
