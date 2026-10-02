"""Reserved /api/v1/entities boundary. Product handlers intentionally deferred."""

from fastapi import APIRouter

router = APIRouter(prefix="/entities", tags=["entities"])
