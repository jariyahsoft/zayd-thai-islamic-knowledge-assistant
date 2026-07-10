from __future__ import annotations

from typing import Literal, cast
from urllib.parse import urlparse

from pydantic import SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "local", "production", "test"]
Language = Literal["ar", "en", "th"]
Madhhab = Literal["hanafi", "hanbali", "maliki", "shafii"]
LogLevel = Literal["DEBUG", "ERROR", "INFO", "WARNING"]
LlmProvider = Literal["local", "ollama", "openai_compatible", "vllm"]
EmbeddingProvider = Literal["local", "openai_compatible"]
S3AddressingStyle = Literal["auto", "path", "virtual"]

LOCAL_ONLY_HOSTS = {"127.0.0.1", "::1", "localhost", "ollama", "vllm"}
PRODUCTION_UNSAFE_SECRETS = {
    "change-me",
    "dev-jwt-secret-change-me",
    "dev-session-secret-change-me",
    "development-only",
    "minioadmin",
    "placeholder",
    "redacted-placeholder",
    "zayd_dev",
}


class EnvironmentConfigurationError(ValueError):
    pass


def _parse_url(value: str, field_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "postgresql", "redis"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid absolute URL")
    return value


def mask_secret(value: str) -> str:
    if len(value) <= 4:
        return "[redacted]"
    return f"{value[:2]}...[redacted]...{value[-2:]}"


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str
    environment: Environment = "local"
    app_url: str = "http://localhost:3100"
    database_url: str = "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev"
    redis_url: str = "redis://redis:6379/0"
    s3_endpoint: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_access_key: SecretStr = SecretStr("minioadmin")
    s3_secret_key: SecretStr = SecretStr("minioadmin")
    s3_bucket: str = "zayd-private"
    s3_addressing_style: S3AddressingStyle = "auto"
    s3_max_attempts: int = 3
    s3_signed_url_ttl_seconds: int = 300
    llm_provider: LlmProvider = "openai_compatible"
    llm_base_url: str = "http://ollama:11434"
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    embedding_provider: EmbeddingProvider = "local"
    embedding_base_url: str | None = None
    embedding_api_key: SecretStr | None = None
    embedding_model: str | None = None
    embedding_revision: str | None = None
    embedding_dimensions: int = 128
    embedding_batch_size: int = 32
    embedding_timeout_seconds: int = 20
    embedding_max_retries: int = 1
    default_language: Language = "th"
    default_madhhab: Madhhab = "shafii"
    enable_external_providers: bool = False
    enable_guest_mode: bool = True
    pilot_mode: bool = False
    pilot_invite_email_hashes: SecretStr | None = None
    pilot_invite_allowlist_version: str | None = None
    guest_session_ttl_minutes: int = 120
    guest_message_quota: int = 10
    log_level: LogLevel = "INFO"
    auth_jwt_secret: SecretStr = SecretStr("dev-jwt-secret-change-me")
    auth_session_secret: SecretStr = SecretStr("dev-session-secret-change-me")
    provider_token: SecretStr = SecretStr("redacted-placeholder")
    allowed_origins: str = "http://localhost:3000,http://localhost:3100,http://localhost:3200"

    @field_validator("app_url")
    @classmethod
    def validate_app_url(cls, value: str) -> str:
        return _parse_url(value, "APP_URL")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        return _parse_url(value, "DATABASE_URL")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        return _parse_url(value, "REDIS_URL")

    @field_validator("s3_endpoint")
    @classmethod
    def validate_s3_endpoint(cls, value: str) -> str:
        return _parse_url(value, "S3_ENDPOINT")

    @field_validator(
        "s3_max_attempts",
        "s3_signed_url_ttl_seconds",
        "embedding_dimensions",
        "embedding_batch_size",
        "embedding_timeout_seconds",
        "embedding_max_retries",
    )
    @classmethod
    def validate_positive_s3_ints(cls, value: int) -> int:
        if value < 1:
            raise ValueError("value must be greater than or equal to 1")
        return value

    @field_validator("s3_signed_url_ttl_seconds")
    @classmethod
    def validate_signed_url_ttl(cls, value: int) -> int:
        if value > 900:
            raise ValueError("S3_SIGNED_URL_TTL_SECONDS must be less than or equal to 900")
        return value

    @field_validator("llm_base_url")
    @classmethod
    def validate_llm_base_url(cls, value: str) -> str:
        return _parse_url(value, "LLM_BASE_URL")

    @field_validator("embedding_base_url")
    @classmethod
    def validate_embedding_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _parse_url(value, "EMBEDDING_BASE_URL")

    @model_validator(mode="after")
    def validate_runtime_rules(self) -> ServiceSettings:
        if not self.enable_external_providers:
            if self.embedding_provider != "local":
                raise ValueError(
                    "EMBEDDING_PROVIDER must be local when ENABLE_EXTERNAL_PROVIDERS=false",
                )

            llm_host = urlparse(self.llm_base_url).hostname
            if self.llm_provider == "openai_compatible" and llm_host not in LOCAL_ONLY_HOSTS:
                raise ValueError(
                    "LLM_BASE_URL must point to a local endpoint when "
                    "ENABLE_EXTERNAL_PROVIDERS=false",
                )

        if self.embedding_provider == "openai_compatible":
            if self.embedding_base_url is None:
                raise ValueError(
                    "EMBEDDING_BASE_URL is required when EMBEDDING_PROVIDER=openai_compatible",
                )
            if self.embedding_model is None:
                raise ValueError(
                    "EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=openai_compatible",
                )

        if self.environment == "production":
            for key, secret_value in (
                ("AUTH_JWT_SECRET", self.auth_jwt_secret),
                ("AUTH_SESSION_SECRET", self.auth_session_secret),
                ("S3_ACCESS_KEY", self.s3_access_key),
                ("S3_SECRET_KEY", self.s3_secret_key),
            ):
                plain_secret = secret_value.get_secret_value().lower()
                if plain_secret in PRODUCTION_UNSAFE_SECRETS:
                    raise ValueError(
                        f"{key} must not use a development placeholder in production",
                    )

        if self.pilot_mode:
            if self.enable_guest_mode:
                raise ValueError("ENABLE_GUEST_MODE must be false when PILOT_MODE=true")
            if not self.pilot_invite_hashes():
                raise ValueError("PILOT_INVITE_EMAIL_HASHES is required when PILOT_MODE=true")
            if not self.pilot_invite_allowlist_version:
                raise ValueError(
                    "PILOT_INVITE_ALLOWLIST_VERSION is required when PILOT_MODE=true"
                )

        return self

    @classmethod
    def from_runtime_env(cls, *, app_name: str) -> ServiceSettings:
        try:
            return cls(
                app_name=app_name,
                environment=cast(Environment, _get_env("APP_ENV", "local")),
                app_url=_get_env("APP_URL", "http://localhost:3100"),
                database_url=_get_env(
                    "DATABASE_URL",
                    "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev",
                ),
                redis_url=_get_env("REDIS_URL", "redis://redis:6379/0"),
                s3_endpoint=_get_env("S3_ENDPOINT", "http://minio:9000"),
                s3_region=_get_env("S3_REGION", "us-east-1"),
                s3_access_key=SecretStr(_get_env("S3_ACCESS_KEY", "minioadmin")),
                s3_secret_key=SecretStr(_get_env("S3_SECRET_KEY", "minioadmin")),
                s3_bucket=_get_env("S3_BUCKET", "zayd-private"),
                s3_addressing_style=cast(
                    S3AddressingStyle,
                    _get_env("S3_ADDRESSING_STYLE", "auto"),
                ),
                s3_max_attempts=int(_get_env("S3_MAX_ATTEMPTS", "3")),
                s3_signed_url_ttl_seconds=int(_get_env("S3_SIGNED_URL_TTL_SECONDS", "300")),
                llm_provider=cast(
                    LlmProvider,
                    _get_env("LLM_PROVIDER", "openai_compatible"),
                ),
                llm_base_url=_get_env("LLM_BASE_URL", "http://ollama:11434"),
                llm_api_key=_optional_secret("LLM_API_KEY"),
                llm_model=_optional_str("LLM_MODEL"),
                embedding_provider=cast(
                    EmbeddingProvider,
                    _get_env("EMBEDDING_PROVIDER", "local"),
                ),
                embedding_base_url=_optional_str("EMBEDDING_BASE_URL"),
                embedding_api_key=_optional_secret("EMBEDDING_API_KEY"),
                embedding_model=_optional_str("EMBEDDING_MODEL"),
                embedding_revision=_optional_str("EMBEDDING_REVISION"),
                embedding_dimensions=int(_get_env("EMBEDDING_DIMENSIONS", "128")),
                embedding_batch_size=int(_get_env("EMBEDDING_BATCH_SIZE", "32")),
                embedding_timeout_seconds=int(_get_env("EMBEDDING_TIMEOUT_SECONDS", "20")),
                embedding_max_retries=int(_get_env("EMBEDDING_MAX_RETRIES", "1")),
                default_language=cast(Language, _get_env("DEFAULT_LANGUAGE", "th")),
                default_madhhab=cast(Madhhab, _get_env("DEFAULT_MADHHAB", "shafii")),
                enable_external_providers=_get_bool("ENABLE_EXTERNAL_PROVIDERS", False),
                enable_guest_mode=_get_bool("ENABLE_GUEST_MODE", True),
                pilot_mode=_get_bool("PILOT_MODE", False),
                pilot_invite_email_hashes=_optional_secret("PILOT_INVITE_EMAIL_HASHES"),
                pilot_invite_allowlist_version=_optional_str("PILOT_INVITE_ALLOWLIST_VERSION"),
                log_level=cast(LogLevel, _get_env("LOG_LEVEL", "INFO")),
                auth_jwt_secret=SecretStr(
                    _get_env("AUTH_JWT_SECRET", "dev-jwt-secret-change-me"),
                ),
                auth_session_secret=SecretStr(
                    _get_env("AUTH_SESSION_SECRET", "dev-session-secret-change-me"),
                ),
                provider_token=SecretStr(_get_env("PROVIDER_TOKEN", "redacted-placeholder")),
            )
        except ValidationError as exc:
            raise EnvironmentConfigurationError(_sanitize_validation_error(exc)) from exc

    def pilot_invite_hashes(self) -> frozenset[str]:
        if self.pilot_invite_email_hashes is None:
            return frozenset()
        values = {
            item.strip().lower()
            for item in self.pilot_invite_email_hashes.get_secret_value().split(",")
            if item.strip()
        }
        if not values or any(
            len(item) != 64 or not all(char in "0123456789abcdef" for char in item)
            for item in values
        ):
            raise ValueError("PILOT_INVITE_EMAIL_HASHES must contain SHA-256 hex digests")
        return frozenset(values)


def _get_bool(name: str, default: bool) -> bool:
    import os

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    if raw_value == "true":
        return True
    if raw_value == "false":
        return False
    raise EnvironmentConfigurationError(f"{name} must be either 'true' or 'false'")


def _get_env(name: str, default: str) -> str:
    import os

    value = os.getenv(name, default).strip()
    if not value:
        raise EnvironmentConfigurationError(f"{name} is required")
    return value


def _optional_secret(name: str) -> SecretStr | None:
    import os

    value = os.getenv(name, "").strip()
    return SecretStr(value) if value else None


def _optional_str(name: str) -> str | None:
    import os

    value = os.getenv(name, "").strip()
    return value or None


def _sanitize_validation_error(error: ValidationError) -> str:
    parts: list[str] = []
    for issue in error.errors():
        field_name = ".".join(str(part) for part in issue["loc"])
        parts.append(f"{field_name}: {issue['msg']}")
    return "Invalid environment configuration: " + "; ".join(parts)
