"""S3 adapter; business modules depend on ObjectStorage, never boto3 or MinIO."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client
from aegis.media.storage import ObjectMetadata


class S3ObjectStorage:
    def __init__(
        self, *, endpoint_url: str, access_key: str, secret_key: str, bucket: str, region: str
    ) -> None:
        self.bucket = bucket
        self.client: S3Client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                connect_timeout=2,
                read_timeout=3,
                retries={"max_attempts": 0},
                s3={"addressing_style": "path"},
            ),
        )

    async def ready(self) -> None:
        await asyncio.to_thread(self.client.head_bucket, Bucket=self.bucket)

    async def put_object(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def get_object(self, key: str) -> bytes:
        def read() -> bytes:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            try:
                return response["Body"].read()
            finally:
                response["Body"].close()

        return await asyncio.to_thread(read)

    async def delete_object(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)

    async def exists(self, key: str) -> bool:
        try:
            await self.metadata(key)
        except ClientError as exc:
            if exc.response["Error"].get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    async def metadata(self, key: str) -> ObjectMetadata:
        result = await asyncio.to_thread(self.client.head_object, Bucket=self.bucket, Key=key)
        return ObjectMetadata(
            size_bytes=result["ContentLength"],
            content_type=result.get("ContentType", "application/octet-stream"),
            etag=result.get("ETag"),
        )
