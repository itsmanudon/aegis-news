"""Reserved /api/v1/search boundary. Product handlers intentionally deferred."""

from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["search"])
