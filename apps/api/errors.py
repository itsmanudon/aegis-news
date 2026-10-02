from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from aegis.contracts.api import ApiErrorEnvelope, ErrorCode, ErrorDetail

HTTP_CODES = {
    400: ErrorCode.INVALID_ARGUMENT,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.INVALID_ARGUMENT,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.INVALID_ARGUMENT,
    429: ErrorCode.RATE_LIMITED,
    503: ErrorCode.SOURCE_UNAVAILABLE,
}


class ApiException(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int) -> None:
        self.code, self.message, self.status_code = code, message, status_code


def error_response(request: Request, code: ErrorCode, message: str, status: int) -> JSONResponse:
    envelope = ApiErrorEnvelope(
        error=ErrorDetail(
            code=code, message=message, request_id=getattr(request.state, "request_id", "unknown")
        )
    )
    return JSONResponse(status_code=status, content=envelope.model_dump(mode="json"))


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def api_error(request: Request, exc: ApiException) -> JSONResponse:
        return error_response(request, exc.code, exc.message, exc.status_code)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = HTTP_CODES.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        response = error_response(
            request, code, code.value.replace("_", " ").capitalize(), exc.status_code
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(request, ErrorCode.INVALID_ARGUMENT, "Request validation failed", 422)
