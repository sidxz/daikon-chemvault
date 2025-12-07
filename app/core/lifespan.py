"""Application lifespan handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging_config import logger
from app.db.initializer import initialize_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    logger.info("Initializing db")
    await initialize_db()
    logger.info("Ready to accept requests")
    yield
    logger.info("Application shutdown")

