from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import SessionLocal

from app.core.logging_config import logger


router = APIRouter()


# Dependency to get the database session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

@router.get("/version")
async def version():
    return {"version": "1.2.1"}
