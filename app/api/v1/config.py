from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import SessionLocal
import pandas as pd
from app.core.logging_config import logger


router = APIRouter()


# Dependency to get the database session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@router.get("/health")
async def health():
    return {
        "service": "chemvault-api",
        "versionName": "rc-2",
        "timestamp": pd.Timestamp.now().isoformat(),
        "version": "1.5.0",
    }
