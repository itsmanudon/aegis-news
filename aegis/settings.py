from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_", env_file=".env", extra="ignore", frozen=True
    )
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://aegis:aegis_dev_only@localhost:5432/aegisnews"
    )
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: SecretStr = SecretStr("aegis_dev")
    s3_secret_key: SecretStr = SecretStr("aegis_dev_only")
    s3_bucket: str = "aegisnews"
    s3_region: str = "us-east-1"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "aegis-foundation"
    temporal_enabled: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    log_file: str = ""
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4318/v1/traces"


@lru_cache
def get_settings() -> Settings:
    return Settings()
