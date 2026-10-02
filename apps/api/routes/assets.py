"""Reserved /api/v1/assets boundary. Product handlers intentionally deferred."""

from fastapi import APIRouter

router = APIRouter(prefix="/assets", tags=["assets"])
