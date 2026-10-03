"""Enforce a body budget before FastAPI's JSON parser materializes ingestion requests."""

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aegis.contracts.api import ErrorCode
from apps.api.errors import error_response

MAX_HTTP_BODY_BYTES = 4 * 1024 * 1024


class IngestionBodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not scope["path"].startswith(("/api/v1/ingestions", "/api/v1/sources"))
        ):
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_HTTP_BODY_BYTES:
                response = error_response(
                    Request(scope),
                    ErrorCode.INVALID_ARGUMENT,
                    "Request exceeds ingestion size limit",
                    422,
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        consumed = False

        async def bounded_receive() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
