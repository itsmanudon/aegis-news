"""Infrastructure composition shared by worker and API."""

from aegis.ingestion.repository import IngestionRepository
from aegis.ingestion.service import IngestionService
from aegis.media.s3 import S3ObjectStorage
from aegis.persistence.database import make_engine, session_factory
from aegis.settings import Settings


def make_service(settings: Settings) -> IngestionService:
    storage = S3ObjectStorage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key.get_secret_value(),
        secret_key=settings.s3_secret_key.get_secret_value(),
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )
    return IngestionService(
        IngestionRepository(session_factory(make_engine(settings))),
        storage,
        settings.s3_bucket,
    )
