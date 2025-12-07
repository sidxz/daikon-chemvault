"""Centralized application settings configured via environment variables.

This module uses :class:`pydantic_settings.BaseSettings` to load configuration
from the environment (and optionally a ``.env`` file). The ``get_settings``
function is memoized so configuration is parsed only once during application
startup.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import AliasChoices, BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    """General application configuration."""

    name: str = Field(default="ChemVault")
    environment: str = Field(default="production")
    rdkit_enabled: bool = Field(default=True)
    rdkit_pains_filter_enabled: bool = Field(default=True)


class DatabaseSettings(BaseModel):
    """Database connectivity configuration."""

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/chemvault",
        validation_alias=AliasChoices("DATABASE__URL", "DATABASE_URL"),
    )
    pool_size: int = Field(default=10, validation_alias=AliasChoices("DATABASE__POOL_SIZE", "DATABASE_POOL_SIZE"))
    max_overflow: int = Field(default=20, validation_alias=AliasChoices("DATABASE__MAX_OVERFLOW", "DATABASE_MAX_OVERFLOW"))
    pool_timeout: int = Field(default=30, validation_alias=AliasChoices("DATABASE__POOL_TIMEOUT", "DATABASE_POOL_TIMEOUT"))
    pool_recycle: int = Field(default=1800, validation_alias=AliasChoices("DATABASE__POOL_RECYCLE", "DATABASE_POOL_RECYCLE"))
    echo: bool = Field(default=False, validation_alias=AliasChoices("DATABASE__ECHO", "DATABASE_ECHO"))


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", validation_alias=AliasChoices("LOGGING__LEVEL", "LOG_LEVEL"))
    json_output: bool = Field(default=False, validation_alias=AliasChoices("LOGGING__JSON", "LOG_JSON"))
    rotation: str = Field(default="10 MB")
    retention: str = Field(default="10 days")
    directory: Path = Field(default=Path("var") / "logs")


class SecuritySettings(BaseModel):
    """Security related configuration such as CORS and allowed hosts."""

    allowed_hosts: List[str] = Field(default_factory=list, validation_alias=AliasChoices("SECURITY__ALLOWED_HOSTS", "ALLOWED_HOSTS"))
    cors_origins: List[str] = Field(default_factory=list, validation_alias=AliasChoices("SECURITY__CORS_ORIGINS", "CORS_ORIGINS"))

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: Union[str, List[str], None]) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    database_url: str | None = Field(default=None, validation_alias=AliasChoices("DATABASE__URL", "DATABASE_URL"))
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    def model_post_init(self, __context):
        if self.database_url:
            self.database.url = self.database_url
        super().model_post_init(__context)


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of :class:`Settings`."""

    return Settings()


settings = get_settings()
