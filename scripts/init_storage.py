"""Idempotently initialize only the local development bucket."""

import asyncio

from botocore.exceptions import ClientError

from aegis.settings import get_settings
from apps.api.dependencies import ReadinessProbe


async def main() -> None:
    probe = ReadinessProbe(get_settings())
    try:
        try:
            await asyncio.to_thread(probe.storage.client.create_bucket, Bucket=probe.storage.bucket)
        except ClientError as exc:
            if exc.response["Error"].get("Code") not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise
        await probe.storage.ready()
    finally:
        await probe.close()


if __name__ == "__main__":
    asyncio.run(main())
