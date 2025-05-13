from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.base import SessionLocal
from app.schemas.cluster_dto import ClusterInputDto, ClusterOutputDto
from app.schemas.pains_dto import PainsOutputDto
from app.services.molcal.cluster import cluster_molecules_with_centroids
from app.core.logging_config import logger
import time

router = APIRouter()


# Dependency to get the database session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@router.post("/cluster", response_model=List[ClusterOutputDto])
async def cluster_molecules(
    molecules: List[ClusterInputDto],
    cutoff: float = 0.7,
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info(f"Clustering request received with {len(molecules)} molecules.")

        # Start time for measuring the clustering duration
        start_time = time.time()

        # Perform the clustering
        result = cluster_molecules_with_centroids(
            molecule_list=molecules, cutoff=cutoff
        )

        # End time after clustering
        end_time = time.time()

        # Calculate the time taken for clustering
        duration = end_time - start_time
        logger.info(f"Clustering completed in {duration:.4f} seconds.")

        return result

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/pains", response_model=List[PainsOutputDto])
async def detect_pains(
    molecules: List[ClusterInputDto], db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(
            f"PAINS detection request received with {len(molecules)} molecules."
        )

        # Start time for measuring the PAINS detection duration
        start_time = time.time()

        # Perform the PAINS detection
        from app.services.molcal.rd_pains import detect_pains

        result = detect_pains(molecules)

        # End time after PAINS detection
        end_time = time.time()

        # Calculate the time taken for PAINS detection
        duration = end_time - start_time
        logger.info(f"PAINS detection completed in {duration:.4f} seconds.")

        return result

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
