import asyncio
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.db.base import SessionLocal
from app.repositories import admet_prediction as repo
from app.schemas.admet_dto import (
    AdmetCalcResultDto,
    AdmetPredictionDto,
)
from app.services.admet.backfill import run_backfill
from app.services.admet.predictor import get_model_version, predict_batch

# Cap for the sync /predict endpoint. At ~13 ms/mol post-warmup this keeps a
# single request under ~3 s; larger jobs should go through molecule
# registration (inline-trigger) or /admet/backfill instead.
PREDICT_SYNC_MAX = 200

router = APIRouter()


async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


def _to_dto(row) -> AdmetPredictionDto:
    return AdmetPredictionDto(
        id=row.id,
        status=row.status,
        predictions=row.predictions,
        model_version=row.model_version,
        error=row.error,
    )


@router.post("/predict", response_model=List[AdmetCalcResultDto])
async def predict(smiles_list: List[str]):
    """
    Stateless ADMET calculation: compute and return predictions inline for
    arbitrary SMILES. Nothing is persisted. Use this for ad-hoc/exploratory
    queries (e.g. frontend previews of unregistered molecules).

    For persisted predictions on registered molecules, use:
      - molecule registration (auto-triggers ADMET via background task), or
      - POST /admet/backfill to catch up missing rows.
    """
    if not smiles_list:
        raise HTTPException(status_code=400, detail="No SMILES supplied.")
    if len(smiles_list) > PREDICT_SYNC_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"At most {PREDICT_SYNC_MAX} SMILES per request; for larger "
                   f"workloads use /admet/backfill.",
        )

    logger.info(f"ADMET sync predict: {len(smiles_list)} SMILES")
    results = await asyncio.to_thread(predict_batch, smiles_list)
    smi_to_props = dict(results)
    version = get_model_version()

    return [
        AdmetCalcResultDto(
            smiles=smi,
            predictions=smi_to_props.get(smi),
            model_version=version if smi in smi_to_props else None,
            error=None if smi in smi_to_props else "Invalid SMILES (rejected by admet_ai)",
        )
        for smi in smiles_list
    ]


@router.post("/backfill", status_code=202)
async def backfill(
    background_tasks: BackgroundTasks,
    chunk_size: int = Query(1000, ge=1, le=5000),
    limit: Optional[int] = Query(None, ge=1),
    include_errors: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Kick off a background backfill job. Returns immediately with the pre-run
    counts breakdown. Poll GET /admet/backfill/status to watch progress.
    """
    counts = await repo.get_status_counts(db)
    logger.info(
        f"ADMET backfill triggered: chunk_size={chunk_size} limit={limit} "
        f"include_errors={include_errors} pre_counts={counts}"
    )
    background_tasks.add_task(
        run_backfill,
        chunk_size=chunk_size,
        limit=limit,
        include_errors=include_errors,
    )
    return {
        "queued": True,
        "chunk_size": chunk_size,
        "limit": limit,
        "include_errors": include_errors,
        "pre_counts": counts,
    }


@router.get("/backfill/status")
async def backfill_status(db: AsyncSession = Depends(get_db)):
    """Counts breakdown across the ADMET prediction lifecycle."""
    return await repo.get_status_counts(db)


@router.get("/{molecule_id}", response_model=AdmetPredictionDto)
async def get_one(molecule_id: UUID4, db: AsyncSession = Depends(get_db)):
    row = await repo.get_by_id(db, molecule_id)
    if not row:
        raise HTTPException(
            status_code=404, detail="No ADMET prediction for this molecule."
        )
    return _to_dto(row)


@router.post("/by-ids", response_model=List[AdmetPredictionDto])
async def get_many(ids: List[UUID4], db: AsyncSession = Depends(get_db)):
    rows = await repo.get_by_ids(db, ids)
    return [_to_dto(r) for r in rows]
