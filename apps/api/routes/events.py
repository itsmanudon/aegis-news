"""Reserved /api/v1/events boundary. Product handlers intentionally deferred."""

from fastapi import APIRouter

router = APIRouter(prefix="/events", tags=["events"])
