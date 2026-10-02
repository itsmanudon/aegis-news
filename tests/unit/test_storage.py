from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from aegis.media.s3 import S3ObjectStorage


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
async def test_exists_only_treats_missing_objects_as_absent(code):
    storage = object.__new__(S3ObjectStorage)
    storage.metadata = AsyncMock(side_effect=ClientError({"Error": {"Code": code}}, "HeadObject"))
    assert await storage.exists("synthetic-key") is False


async def test_exists_propagates_access_denial():
    storage = object.__new__(S3ObjectStorage)
    storage.metadata = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")
    )
    with pytest.raises(ClientError):
        await storage.exists("synthetic-key")
