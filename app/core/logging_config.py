# core/logging_config.py

import sys
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables from a .env file if present
load_dotenv()

# Determine logging level and format from environment variables
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
log_json = os.getenv("LOG_JSON", "False").lower() == "true"

# Remove the default Loguru logger configuration to apply custom settings
logger.remove()

# Configure the logger to output to stderr with optional JSON serialization
logger.add(sys.stderr, level=log_level, serialize=log_json)

# Define the project root directory and the logs directory
project_root = Path(__file__).resolve().parent.parent
log_directory = project_root / "var" / "logs"

# Ensure the logs directory exists, creating it if necessary
log_directory.mkdir(parents=True, exist_ok=True)

# Set the absolute path for the log file
log_file_path = log_directory / "app.log"

# Configure the logger to write to a file with rotation and retention policies
logger.add(
    log_file_path,
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    serialize=log_json
)
