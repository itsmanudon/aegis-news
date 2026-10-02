from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResponseMeta(Contract):
    request_id: str = Field(min_length=1, max_length=128)
    api_version: Literal["v1"] = "v1"


class SingleResponse[T](Contract):
    data: T
    meta: ResponseMeta


class CursorPagination(Contract):
    next_cursor: str | None = Field(default=None, min_length=1)
    has_more: bool = False

    @model_validator(mode="after")
    def consistent_cursor(self) -> "CursorPagination":
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more and next_cursor must agree")
        return self


class CollectionResponse[T](Contract):
    data: tuple[T, ...]
    pagination: CursorPagination
    meta: ResponseMeta


class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    INTEGRITY_FAILED = "INTEGRITY_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(Contract):
    code: ErrorCode
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=128)


class ApiErrorEnvelope(Contract):
    error: ErrorDetail


class HealthStatus(Contract):
    status: Literal["ok"] = "ok"


class DependencyStatus(Contract):
    name: Literal["postgres", "redis", "object_storage", "temporal"]
    ready: bool


class ReadinessStatus(Contract):
    status: Literal["ready", "not_ready"]
    dependencies: tuple[DependencyStatus, ...]


class SystemInfo(Contract):
    name: Literal["AegisNews"] = "AegisNews"
    version: str
    stage: Literal["foundation"] = "foundation"
    architecture: Literal["modular monolith + background workers"] = (
        "modular monolith + background workers"
    )
