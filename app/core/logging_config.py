"""Logging configuration built from application settings."""

import sys
from pathlib import Path

from loguru import logger

from app.core.settings import get_settings


def configure_logging() -> None:
    """Configure Loguru based on the current settings."""

    settings = get_settings()
    log_level = settings.logging.level.upper()
    log_json = settings.logging.json

    logger.remove()
    logger.add(sys.stderr, level=log_level, serialize=log_json)

    project_root = Path(__file__).resolve().parent.parent.parent
    log_directory = project_root / settings.logging.directory
    log_directory.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_directory / "app.log",
        rotation=settings.logging.rotation,
        retention=settings.logging.retention,
        level=log_level,
        serialize=log_json,
    )


configure_logging()
