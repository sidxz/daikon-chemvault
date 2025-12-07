"""Centralized application settings configured via environment variables.

This module uses :class:`pydantic_settings.BaseSettings` to load configuration
from the environment (and optionally a ``.env`` file). The ``get_settings``
function is memoized so configuration is parsed only once during application
startup.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    database_url: str = "sqlite+aiosqlite:///:memory:"
    log_level: str = "INFO"
    log_json: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of :class:`Settings`."""

    return Settings()


settings = get_settings()
