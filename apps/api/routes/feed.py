"""Incremental feed for a scheduled downstream sync."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from aegis.contracts.api import CursorPagination, ErrorCode, ResponseMeta
from aegis.contracts.feed import FeedResponse
from aegis.intelligence import feed
from aegis.security.auth import product_access
from apps.api.errors import ApiException
from apps.api.routes.ingestions import repository

# feed:read covers the bundle and nothing else, so a consumer that only syncs the feed
# holds no scope that reaches article text or the write routes.
router = APIRouter(tags=["feed"], dependencies=[product_access("feed:read")])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=feed.CURSOR_MAXIMUM)]
Since = Annotated[AwareDatetime | None, Query()]
Text = Annotated[str | None, Query(min_length=1, max_length=512)]


@router.get("/feed/documents", response_model=FeedResponse)
def documents(
    request: Request,
    limit: Limit = 50,
    cursor: Cursor = None,
    since: Since = None,
    mapped: bool = False,
    scheme: Literal["exchange_symbol", "isin", "provider_id"] | None = None,
    venue: Text = None,
    identifier: Text = None,
) -> FeedResponse:
    """Signed documents after a position, oldest first, without article text.

    Start with ``since`` or with neither parameter, then pass back ``resume_cursor``.
    It is always present, also when the page is empty, so the next sync resumes from it.

    ``mapped`` keeps only documents linked to at least one instrument. ``scheme``,
    ``venue`` and ``identifier`` narrow that to matching listings and imply ``mapped``.
    A cursor belongs to the filters it was issued with.
    """
    listing = {
        key: value
        for key, value in (("scheme", scheme), ("venue", venue), ("identifier", identifier))
        if value is not None
    }
    filters: dict[str, object] = {"kind": "feed"}
    if mapped or listing:
        filters["instrument"] = listing
    if cursor is not None and since is not None:
        raise ApiException(ErrorCode.INVALID_ARGUMENT, "Give cursor or since, not both", 422)
    try:
        after = (
            feed.decode_position(cursor, filters)
            if cursor is not None
            else (since.astimezone(UTC), "")
            if since is not None
            else feed.START
        )
    except ValueError:
        raise ApiException(ErrorCode.INVALID_ARGUMENT, "Invalid feed cursor", 422) from None
    bound = datetime.now(UTC) - feed.SAFETY_LAG
    with repository(request).sessions() as session:
        items, more = feed.read(
            session, after, bound, limit, listing if (mapped or listing) else None
        )
    last = (items[-1].document.last_signed_at, items[-1].document.document_id) if items else after
    position = feed.encode_position(last, filters)
    return FeedResponse(
        data=tuple(items),
        as_of=bound,
        pagination=CursorPagination(has_more=more, next_cursor=position if more else None),
        resume_cursor=position,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
