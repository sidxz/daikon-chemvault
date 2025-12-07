# core/logging_config.py

import sys
from pathlib import Path

from loguru import logger

from app.core.settings import settings


def configure_logging() -> None:
    """Configure Loguru based on the current settings."""

    log_level = settings.log_level.upper()
    log_json = settings.log_json

    logger.remove()
    logger.add(sys.stderr, level=log_level, serialize=log_json)

    project_root = Path(__file__).resolve().parent.parent.parent
    log_directory = project_root / "var" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_directory / "app.log",
        rotation="10 MB",
        retention="10 days",
        level=log_level,
        serialize=log_json,
    )


configure_logging()
