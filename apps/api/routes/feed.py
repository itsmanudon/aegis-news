"""Incremental feed for a scheduled downstream sync."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from aegis.contracts.api import CursorPagination, ErrorCode, ResponseMeta
from aegis.contracts.feed import FeedResponse
from aegis.intelligence import feed
from aegis.security.auth import product_access
from apps.api.errors import ApiException
from apps.api.routes.ingestions import repository

# A bundle embeds events, so the caller needs both scopes; one dependency keeps the
# token validated, and the rate limit counted, once per request.
router = APIRouter(tags=["feed"], dependencies=[product_access("documents:read", "events:read")])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=feed.CURSOR_MAXIMUM)]
Since = Annotated[AwareDatetime | None, Query()]


@router.get("/feed/documents", response_model=FeedResponse)
def documents(
    request: Request, limit: Limit = 50, cursor: Cursor = None, since: Since = None
) -> FeedResponse:
    """Signed documents after a position, oldest first, without article text.

    Start with ``since`` or with neither parameter, then pass back ``resume_cursor``.
    It is always present, also when the page is empty, so the next sync resumes from it.
    """
    filters = {"kind": "feed"}
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
        items, more = feed.read(session, after, bound, limit)
    last = (items[-1].document.last_signed_at, items[-1].document.document_id) if items else after
    position = feed.encode_position(last, filters)
    return FeedResponse(
        data=tuple(items),
        as_of=bound,
        pagination=CursorPagination(has_more=more, next_cursor=position if more else None),
        resume_cursor=position,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
