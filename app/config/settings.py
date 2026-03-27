from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(alias="APP_NAME")
    app_env: str = Field(alias="APP_ENV")
    app_port: int = Field(alias="APP_PORT")
    app_domain: str = Field(alias="APP_DOMAIN")
    static_root_path: Path = Field(alias="STATIC_ROOT_PATH")
    assets_root_path: Path = Field(alias="ASSETS_ROOT_PATH")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    magic_link_expire_minutes: int = Field(default=15, alias="MAGIC_LINK_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    admin_access_token_expire_minutes: int = Field(default=15, alias="ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES")
    admin_refresh_token_expire_days: int = Field(default=14, alias="ADMIN_REFRESH_TOKEN_EXPIRE_DAYS")
    admin_jwt_scope: str = Field(default="admin", alias="ADMIN_JWT_SCOPE")
    mail_mailer: str = Field(alias="MAIL_MAILER")
    mail_host: str = Field(alias="MAIL_HOST")
    mail_port: int = Field(alias="MAIL_PORT")
    mail_username: str = Field(alias="MAIL_USERNAME")
    mail_password: str = Field(alias="MAIL_PASSWORD")
    mail_encryption: str = Field(alias="MAIL_ENCRYPTION")
    mail_from_address: str = Field(alias="MAIL_FROM_ADDRESS")
    mail_from_name: str = Field(alias="MAIL_FROM_NAME")
    stripe_secret_key: str = Field(alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_pro: str | None = Field(default=None, alias="STRIPE_PRICE_ID_PRO")
    stripe_price_id_enterprise: str | None = Field(default=None, alias="STRIPE_PRICE_ID_ENTERPRISE")
    subscription_expiry_warning_days: int = Field(default=3, alias="SUBSCRIPTION_EXPIRY_WARNING_DAYS")
    usage_warning_threshold_percent: int = Field(default=80, alias="USAGE_WARNING_THRESHOLD_PERCENT")
    scheduler_subscription_expiry_scan_minutes: int = Field(default=60, alias="SCHEDULER_SUBSCRIPTION_EXPIRY_SCAN_MINUTES")
    admin_api_key: str | None = Field(default=None, alias="ADMIN_API_KEY")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    enable_docs: bool | None = Field(default=None, validation_alias=AliasChoices("ENABLE_DOCS", "API_DOCS_ENABLED"))
    dev_auth_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEV_AUTH_ENABLED", "DEVELOPMENT_AUTH_HEADERS_ENABLED"),
    )
    dev_admin_auth_enabled: bool = Field(default=False, alias="DEV_ADMIN_AUTH_ENABLED")
    allowed_hosts_raw: str = Field(default="", alias="ALLOWED_HOSTS")
    cors_allowed_origins_raw: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")

    @property
    def is_local_env(self) -> bool:
        return self.app_env.lower() in {"local", "development", "dev", "test"}

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return self.enable_docs
        return self.is_local_env

    @property
    def trusted_hosts(self) -> list[str]:
        if self.allowed_hosts:
            return self.allowed_hosts
        if self.is_local_env:
            return ["127.0.0.1", "localhost", self.app_domain, f"*.{self.app_domain}"]
        return [self.app_domain, f"*.{self.app_domain}"]

    @property
    def allowed_hosts(self) -> list[str]:
        return self._split_csv(self.allowed_hosts_raw)

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self._split_csv(self.cors_allowed_origins_raw)

    def _split_csv(self, value: str) -> list[str]:
        stripped = value.strip()
        if not stripped:
            return []
        return [item.strip() for item in stripped.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_runtime_secrets(self) -> "Settings":
        required_values = {
            "DATABASE_URL": self.database_url,
            "SECRET_KEY": self.secret_key,
            "STRIPE_SECRET_KEY": self.stripe_secret_key,
            "STRIPE_WEBHOOK_SECRET": self.stripe_webhook_secret,
        }

        if not self.is_local_env:
            missing = [name for name, value in required_values.items() if not value or not value.strip()]
            if missing:
                names = ", ".join(missing)
                raise ValueError(f"Missing required environment configuration: {names}")

        if not self.is_local_env and self.app_debug:
            raise ValueError("APP_DEBUG must be disabled outside local environments")

        if not self.is_local_env and "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*' outside local environments")

        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")

        if self.refresh_token_expire_days <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")

        if self.magic_link_expire_minutes <= 0:
            raise ValueError("MAGIC_LINK_EXPIRE_MINUTES must be greater than 0")

        if self.admin_access_token_expire_minutes <= 0:
            raise ValueError("ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")

        if self.admin_refresh_token_expire_days <= 0:
            raise ValueError("ADMIN_REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")

        if self.jwt_algorithm != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")

        if self.mail_mailer.strip().lower() != "smtp":
            raise ValueError("MAIL_MAILER must be smtp")

        if self.mail_port <= 0:
            raise ValueError("MAIL_PORT must be greater than 0")

        if self.mail_encryption.strip().lower() not in {"none", "tls", "ssl"}:
            raise ValueError("MAIL_ENCRYPTION must be one of: none, tls, ssl")

        if not self.is_local_env and self.dev_auth_enabled:
            raise ValueError("DEV_AUTH_ENABLED must be disabled outside local environments")

        if not self.is_local_env and self.dev_admin_auth_enabled:
            raise ValueError("DEV_ADMIN_AUTH_ENABLED must be disabled outside local environments")

        if self.dev_admin_auth_enabled and (not self.admin_api_key or not self.admin_api_key.strip()):
            raise ValueError("ADMIN_API_KEY is required when DEV_ADMIN_AUTH_ENABLED is enabled")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
