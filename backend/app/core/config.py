from functools import lru_cache
from json import JSONDecodeError, loads
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/kdafik_racing_manager"
LOCAL_JWT_SECRET = "local-only-secret-change-before-public-use"
LOCAL_EMAIL_CODE_SECRET = "local-only-email-code-secret-change-before-public-use"
LOCAL_TRUSTED_HOSTS = ["localhost", "127.0.0.1", "test", "testserver"]
ALLOWED_CORS_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_CORS_HEADERS = ["Authorization", "Content-Type"]
YANDEX_SMTP_HOST = "smtp.yandex.ru"
YANDEX_SMTP_PORT = 587
YANDEX_SMTP_SENDER = "Kdafik Racing Manager <kdafikracing@yandex.ru>"


class Settings(BaseSettings):
    app_name: str = "Kdafik Racing Manager API"
    app_version: str = "0.1.0"
    # `test` is an internal profile for automated tests; user-facing launches use
    # only `local` or `production`.
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default=LOCAL_DATABASE_URL, repr=False)
    auth_jwt_secret: str = Field(default=LOCAL_JWT_SECRET, repr=False)
    auth_jwt_issuer: str = "kdafik-racing-manager"
    auth_jwt_audience: str = "kdafik-racing-manager-api"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    refresh_cookie_name: str = "kdafik_refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    trusted_hosts: list[str] = Field(default_factory=lambda: LOCAL_TRUSTED_HOSTS.copy())
    email_enabled: bool = False
    email_code_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(LOCAL_EMAIL_CODE_SECRET), repr=False
    )
    email_from_address: str = YANDEX_SMTP_SENDER
    smtp_host: str = YANDEX_SMTP_HOST
    smtp_port: int = YANDEX_SMTP_PORT
    smtp_username: str = Field(default="", repr=False)
    smtp_password: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    smtp_use_tls: bool = True

    # LLM Settings
    llm_enabled: bool = True
    llm_model_path: str = "llm/MiniCPM5-1B-Q4_K_M.gguf"
    llm_context_window: int = 2048
    llm_temperature: float = 0.7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        enable_decoding=False,
        hide_input_in_errors=True,
        extra="ignore",
    )

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_string_list(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return []

        if stripped.startswith("["):
            try:
                return loads(stripped)
            except JSONDecodeError as exc:
                raise ValueError("setting must be JSON or comma-separated") from exc

        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        errors: list[str] = []
        if self.environment == "production" and self.debug:
            errors.append("debug must be disabled")
        if self.environment == "production" and (
            len(self.auth_jwt_secret) < 32
            or self.auth_jwt_secret == LOCAL_JWT_SECRET
            or self._contains_placeholder(self.auth_jwt_secret)
        ):
            errors.append("auth_jwt_secret must be a non-default value of at least 32 characters")
        if self.environment == "production" and (
            not self.auth_jwt_issuer or not self.auth_jwt_audience
        ):
            errors.append("auth_jwt_issuer and auth_jwt_audience must be configured")
        if self.environment == "production" and not self.refresh_cookie_secure:
            errors.append("refresh_cookie_secure must be enabled")
        if self.environment == "production" and self.refresh_cookie_samesite not in {
            "lax",
            "strict",
        }:
            errors.append("refresh_cookie_samesite must be lax or strict")
        if self.environment == "production" and (
            not self.database_url
            or self._contains_placeholder(self.database_url)
            or self.database_url == LOCAL_DATABASE_URL
            or self._is_local_database_url()
        ):
            errors.append("database_url must be a non-local production database URL")
        has_invalid_cors_origin = any(
            not self._is_production_origin(origin) for origin in self.cors_origins
        )
        if self.environment == "production" and (not self.cors_origins or has_invalid_cors_origin):
            errors.append("cors_origins must contain explicit HTTPS origins without wildcards")
        has_invalid_trusted_host = any(
            not self._is_explicit_host(host) for host in self.trusted_hosts
        )
        if self.environment == "production" and (
            not self.trusted_hosts or has_invalid_trusted_host
        ):
            errors.append("trusted_hosts must contain explicit hosts without wildcards")
        if self.email_enabled:
            email_code_secret = self.email_code_secret.get_secret_value()
            if self.environment == "production" and (
                len(email_code_secret) < 32
                or email_code_secret == LOCAL_EMAIL_CODE_SECRET
                or self._contains_placeholder(email_code_secret)
            ):
                errors.append(
                    "email_code_secret must be a non-default value of at least 32 characters"
                )
            if not self.smtp_username or not self.smtp_password.get_secret_value():
                errors.append("SMTP credentials are required when email is enabled")
            if self.email_from_address != YANDEX_SMTP_SENDER:
                errors.append("email_from_address must be the approved Yandex sender")
            if self.smtp_host != YANDEX_SMTP_HOST:
                errors.append("smtp_host must be smtp.yandex.ru when email is enabled")
            if self.smtp_port != YANDEX_SMTP_PORT:
                errors.append("smtp_port must be 587 when email is enabled")
            if not self.smtp_use_tls:
                errors.append("smtp_use_tls must enable STARTTLS when email is enabled")

        if self.environment == "production":
            # Legal text is part of the runtime contract: production must not
            # start with a DRAFT, placeholder, missing source or stale hash.
            from app.services.legal_manifest import validate_runtime_manifest

            try:
                validate_runtime_manifest(environment="production")
            except ValueError as exc:
                errors.append(f"legal manifest is not production-ready: {exc}")

        if errors:
            raise ValueError("Invalid production security configuration: " + "; ".join(errors))
        return self

    def _is_local_database_url(self) -> bool:
        parsed_url = urlparse(self.database_url)
        return not parsed_url.hostname or parsed_url.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
            "db",
        }

    @staticmethod
    def _is_production_origin(origin: str) -> bool:
        parsed_url = urlparse(origin)
        return (
            parsed_url.scheme == "https"
            and bool(parsed_url.hostname)
            and not parsed_url.path.rstrip("/")
            and not parsed_url.params
            and not parsed_url.query
            and not parsed_url.fragment
            and not parsed_url.username
            and not parsed_url.password
            and not Settings._contains_placeholder(origin)
            and "*" not in origin
        )

    @staticmethod
    def _is_explicit_host(host: str) -> bool:
        return (
            bool(host.strip())
            and "*" not in host
            and "://" not in host
            and "/" not in host
            and not Settings._contains_placeholder(host)
        )

    @staticmethod
    def _contains_placeholder(value: str) -> bool:
        normalized = value.lower()
        return (
            "<" in value
            or ">" in value
            or "change-me" in normalized
            or "replace-with" in normalized
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
