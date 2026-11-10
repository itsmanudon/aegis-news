"""Instrument mappings: which listing identifies a curated entity.

Read only. Mappings are written by the seed command (aegis.entities.seed).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime
from sqlalchemy import select

from aegis.contracts.api import CollectionResponse
from aegis.domain.models import AssetMapping
from aegis.intelligence.pipeline import record
from aegis.persistence.models import AssetMappingRow
from apps.api.routes.ingestions import repository
from apps.api.routes.product import page

# main.py attaches the documents:read requirement when security is enabled.
router = APIRouter(prefix="/assets", tags=["assets"])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=128)]
Text = Annotated[str | None, Query(min_length=1, max_length=512)]


@router.get("/mappings", response_model=CollectionResponse[AssetMapping])
def mappings(
    request: Request,
    limit: Limit = 25,
    cursor: Cursor = None,
    as_of: Annotated[AwareDatetime | None, Query()] = None,
    entity_id: Text = None,
    scheme: Literal["exchange_symbol", "isin", "provider_id"] | None = None,
    venue: Text = None,
    identifier: Text = None,
) -> CollectionResponse[AssetMapping]:
    """Mappings ordered by identifier, optionally narrowed to one entity or listing."""
    query = select(AssetMappingRow).order_by(AssetMappingRow.mapping_id).limit(limit + 1)
    if cursor:
        query = query.where(AssetMappingRow.mapping_id > cursor)
    if as_of:
        query = query.where(AssetMappingRow.created_at <= as_of)
    for column, value in (
        (AssetMappingRow.entity_id, entity_id),
        (AssetMappingRow.scheme, scheme),
        (AssetMappingRow.venue, venue),
        (AssetMappingRow.identifier, identifier),
    ):
        if value is not None:
            query = query.where(column == value)
    with repository(request).sessions() as session:
        return page(
            [record(AssetMapping, row) for row in session.scalars(query)],
            limit,
            request,
            lambda value: value.mapping_id,
        )
