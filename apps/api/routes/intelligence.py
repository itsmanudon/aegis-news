"""Snapshot-bounded topic evidence, chronological discovery and corpus aggregates."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime, TypeAdapter

from aegis.contracts.api import CursorPagination, ErrorCode, ResponseMeta, SingleResponse
from aegis.contracts.intelligence import (
    AnalyticsReport,
    DocumentDiscoveryItem,
    SnapshotCollectionResponse,
    TopicMembership,
    TopicSummary,
)
from aegis.domain.ids import DocumentId, SourceId
from aegis.intelligence import read_models as reads
from aegis.security.auth import product_access
from apps.api.errors import ApiException
from apps.api.routes.ingestions import repository

router = APIRouter(tags=["intelligence"], dependencies=[product_access("documents:read")])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=32768)]
Cutoff = Annotated[AwareDatetime | None, Query()]
Search = Annotated[str, Query(max_length=200)]
TopicId = Annotated[str | None, Query(max_length=32777)]
TimeBasis = Literal["published_at", "first_seen_at"]


def invalid() -> ApiException:
    return ApiException(ErrorCode.INVALID_ARGUMENT, "Invalid identity, cursor or time window", 422)


def utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


def window(start: datetime | None, end: datetime | None) -> None:
    if (start is None) != (end is None):
        raise invalid()
    if (
        start is not None
        and end is not None
        and not (timedelta(0) < end - start <= timedelta(days=366))
    ):
        raise invalid()


def identity(value: str | None) -> reads.TopicIdentity | None:
    try:
        return reads.parse_topic_id(value) if value is not None else None
    except ValueError:
        raise invalid() from None


def snapshot(
    cursor: str | None,
    filters: dict[str, Any],
    cutoff: datetime | None,
    kind: Literal["topic", "document"],
) -> tuple[datetime, list[Any] | None]:
    if cursor is None:
        return utc(cutoff) or datetime.now(UTC), None
    try:
        cutoff, key = reads.decode_cursor(cursor, filters, cutoff)
        if kind == "topic":
            # Reuse the full strict identity validation for the directory sort key.
            reads.parse_topic_id(reads.topic_id(cast(reads.TopicIdentity, tuple(key))))
        else:
            if len(key) != 2:
                raise ValueError("invalid chronological key")
            TypeAdapter(DocumentId).validate_python(key[1])
            if key[0] is not None:
                if not isinstance(key[0], str):
                    raise ValueError("invalid chronological timestamp")
                key[0] = TypeAdapter(AwareDatetime).validate_python(key[0]).astimezone(UTC)
        return cutoff, key
    except (ValueError, TypeError):
        raise invalid() from None


def page[T](
    values: list[T],
    limit: int,
    cutoff: datetime,
    request: Request,
    filters: dict[str, Any],
    key: Any,
) -> SnapshotCollectionResponse[T]:
    more = len(values) > limit
    return SnapshotCollectionResponse(
        data=tuple(values[:limit]),
        as_of=cutoff,
        pagination=CursorPagination(
            has_more=more,
            next_cursor=reads.encode_cursor(cutoff, filters, key(values[limit - 1]))
            if more
            else None,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/topics", response_model=SnapshotCollectionResponse[TopicSummary])
def topics(
    request: Request, limit: Limit = 25, cursor: Cursor = None, as_of: Cutoff = None, q: Search = ""
) -> SnapshotCollectionResponse[TopicSummary]:
    filters = {"kind": "topics", "q": q}
    cutoff, after = snapshot(cursor, filters, as_of, "topic")
    with repository(request).sessions() as session:
        values = reads.topics(session, cutoff, limit, q, after)
    return page(
        values,
        limit,
        cutoff,
        request,
        filters,
        lambda value: list(reads.parse_topic_id(value.topic_id)),
    )


@router.get("/topics/{topic_id}", response_model=SingleResponse[TopicSummary])
def topic(topic_id: str, request: Request, as_of: Cutoff = None) -> SingleResponse[TopicSummary]:
    exact = identity(topic_id)
    cutoff = utc(as_of) or datetime.now(UTC)
    with repository(request).sessions() as session:
        values = reads.topics(session, cutoff, 1, "", identity=exact)
    if not values:
        raise ApiException(ErrorCode.NOT_FOUND, "Topic not found at this cutoff", 404)
    return SingleResponse(data=values[0], meta=ResponseMeta(request_id=request.state.request_id))


@router.get(
    "/topics/{topic_id}/documents", response_model=SnapshotCollectionResponse[TopicMembership]
)
def topic_documents(
    topic_id: str, request: Request, limit: Limit = 25, cursor: Cursor = None, as_of: Cutoff = None
) -> SnapshotCollectionResponse[TopicMembership]:
    exact = identity(topic_id)
    filters = {"kind": "topic_documents", "topic_id": topic_id}
    cutoff, after = snapshot(cursor, filters, as_of, "document")
    with repository(request).sessions() as session:
        values = cast(
            list[TopicMembership],
            reads.chronological(session, cutoff, limit, "published_at", after, identity=exact),
        )
    return page(
        values,
        limit,
        cutoff,
        request,
        filters,
        lambda value: [
            value.document.published_at.isoformat() if value.document.published_at else None,
            value.document.document_id,
        ],
    )


@router.get("/discovery", response_model=SnapshotCollectionResponse[DocumentDiscoveryItem])
def discovery(
    request: Request,
    limit: Limit = 25,
    cursor: Cursor = None,
    as_of: Cutoff = None,
    order: TimeBasis = "published_at",
    q: Search = "",
    source_id: SourceId | None = None,
    topic_id: TopicId = None,
    start: Cutoff = None,
    end: Cutoff = None,
    time_basis: TimeBasis = "published_at",
) -> SnapshotCollectionResponse[DocumentDiscoveryItem]:
    start, end = utc(start), utc(end)
    window(start, end)
    exact = identity(topic_id)
    filters = {
        "kind": "discovery",
        "order": order,
        "q": q,
        "source_id": source_id,
        "topic_id": topic_id,
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "time_basis": time_basis,
    }
    cutoff, after = snapshot(cursor, filters, as_of, "document")
    with repository(request).sessions() as session:
        values = reads.chronological(
            session, cutoff, limit, order, after, source_id, q, exact, start, end, time_basis
        )
    return page(
        values,
        limit,
        cutoff,
        request,
        filters,
        lambda value: [
            getattr(value.document, order).isoformat() if getattr(value.document, order) else None,
            value.document.document_id,
        ],
    )


@router.get("/analytics", response_model=SingleResponse[AnalyticsReport])
def analytics(
    request: Request,
    start: Annotated[AwareDatetime, Query()],
    end: Annotated[AwareDatetime, Query()],
    as_of: Cutoff = None,
    time_basis: TimeBasis = "published_at",
    source_id: SourceId | None = None,
    topic_id: TopicId = None,
) -> SingleResponse[AnalyticsReport]:
    normalized_start, normalized_end = start.astimezone(UTC), end.astimezone(UTC)
    window(normalized_start, normalized_end)
    exact = identity(topic_id)
    cutoff = utc(as_of) or datetime.now(UTC)
    with repository(request).sessions() as session:
        value = reads.analytics(
            session, cutoff, normalized_start, normalized_end, time_basis, source_id, exact
        )
    return SingleResponse(data=value, meta=ResponseMeta(request_id=request.state.request_id))
