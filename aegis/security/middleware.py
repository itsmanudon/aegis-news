"""Bound streamed API request bodies before JSON parsing."""

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aegis.contracts.api import ApiErrorEnvelope, ErrorCode, ErrorDetail


class SecurityBodyLimit:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                envelope = ApiErrorEnvelope(
                    error=ErrorDetail(
                        code=ErrorCode.INVALID_ARGUMENT,
                        message="Request body too large",
                        request_id=getattr(Request(scope).state, "request_id", "unknown"),
                    )
                )
                response = JSONResponse(status_code=413, content=envelope.model_dump(mode="json"))
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
