# core/logging_config.py

import sys
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
import os

project_root = Path(__file__).resolve().parent.parent

print(project_root)