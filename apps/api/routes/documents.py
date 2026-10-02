"""Reserved /api/v1/documents boundary. Product handlers intentionally deferred."""

from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])
