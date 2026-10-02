from typing import Protocol

from pydantic import BaseModel, ConfigDict


class ObjectMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    size_bytes: int
    content_type: str
    etag: str | None = None


class ObjectStorage(Protocol):
    async def put_object(self, key: str, content: bytes, content_type: str) -> None: ...
    async def get_object(self, key: str) -> bytes: ...
    async def delete_object(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def metadata(self, key: str) -> ObjectMetadata: ...
