from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
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
    ai_profile: Literal["offline", "light", "full"] = "offline"
    newsdata_api_key: SecretStr = SecretStr("")
    gnews_api_key: SecretStr = SecretStr("")
    newsapi_api_key: SecretStr = SecretStr("")
    youtube_api_key: SecretStr = SecretStr("")
    provider_ingestion_api_url: str = "http://127.0.0.1:8000"
    provenance_key_id: str = "local"
    security_persist_audit: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    log_file: str = ""
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4318/v1/traces"
    environment: Literal["development", "test", "production"] = "development"
    security_enabled: bool = False
    dev_identity_enabled: bool = False
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_public_keys: dict[str, str] = {}
    oidc_algorithms: list[Literal["RS256", "EdDSA"]] = ["RS256"]
    oidc_token_types: list[str] = ["at+jwt"]
    security_key_directory: Path = Path(".keys")
    security_rate_limit: int = 60
    security_rate_backend: Literal["memory", "redis"] = "memory"
    security_max_body_bytes: int = 262144

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if (
            not self.oidc_algorithms
            or not self.oidc_token_types
            or self.security_rate_limit < 1
            or self.security_max_body_bytes < 1
        ):
            raise ValueError("Invalid security policy")
        if self.security_enabled and (not self.oidc_issuer or not self.oidc_audience):
            raise ValueError("Explicit issuer and audience required")
        if self.environment == "production":
            if self.security_rate_backend != "redis":
                raise ValueError("Production requires Redis rate limiting")
            if not self.security_enabled or self.dev_identity_enabled:
                raise ValueError(
                    "Production requires OIDC security and forbids development identity"
                )
            if not self.oidc_issuer.startswith("https://"):
                raise ValueError("Production issuer must use HTTPS")
            if self.oidc_jwks_url and not self.oidc_jwks_url.startswith("https://"):
                raise ValueError("Production JWKS must use HTTPS")
            if not self.oidc_jwks_url and not self.oidc_public_keys:
                raise ValueError("Production requires trusted verification keys")
            if "*" in self.cors_origins:
                raise ValueError("Production CORS requires explicit origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
