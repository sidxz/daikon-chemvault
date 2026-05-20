from sqlalchemy import func, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional, Tuple
from uuid import UUID
from app.db.models.admet_prediction import AdmetPrediction
from app.db.models.molecule import Molecule
from app.core.logging_config import logger


async def get_by_id(db: AsyncSession, molecule_id: UUID) -> Optional[AdmetPrediction]:
    """
    Retrieve an ADMET prediction row for a given molecule ID.
    """
    result = await db.execute(
        select(AdmetPrediction).filter(AdmetPrediction.id == molecule_id)
    )
    return result.scalar()


async def get_by_ids(db: AsyncSession, molecule_ids: List[UUID]) -> List[AdmetPrediction]:
    """
    Retrieve ADMET prediction rows for a list of molecule IDs.
    """
    if not molecule_ids:
        return []
    result = await db.execute(
        select(AdmetPrediction).filter(AdmetPrediction.id.in_(molecule_ids))
    )
    return list(result.scalars().all())


async def upsert_pending(db: AsyncSession, molecule_id: UUID) -> AdmetPrediction:
    """
    Insert a pending ADMET prediction row, or reset an existing row back to pending,
    clearing predictions/error so the next run overwrites stale data.
    """
    stmt = (
        insert(AdmetPrediction)
        .values(id=molecule_id, status="pending", predictions=None, error=None)
        .on_conflict_do_update(
            index_elements=[AdmetPrediction.id],
            set_={"status": "pending", "predictions": None, "error": None},
        )
        .returning(AdmetPrediction)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def bulk_upsert_pending(db: AsyncSession, molecule_ids: List[UUID]) -> int:
    """
    Bulk version of upsert_pending. Issues one INSERT … ON CONFLICT DO UPDATE
    that resets every supplied row to status='pending' and clears stale
    predictions/error. Returns the number of rows touched.
    """
    if not molecule_ids:
        return 0
    values = [
        {"id": mid, "status": "pending", "predictions": None, "error": None}
        for mid in molecule_ids
    ]
    stmt = insert(AdmetPrediction).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AdmetPrediction.id],
        set_={"status": "pending", "predictions": None, "error": None},
    )
    await db.execute(stmt)
    return len(molecule_ids)


async def get_status_counts(db: AsyncSession) -> dict:
    """
    Return a counts breakdown: total molecules, done, pending, error, missing
    (molecules without any admet_predictions row).
    """
    total_q = await db.execute(
        select(func.count())
        .select_from(Molecule)
        .where(Molecule._is_deleted.is_(False))
    )
    total = total_q.scalar_one()

    by_status_q = await db.execute(
        select(AdmetPrediction.status, func.count())
        .group_by(AdmetPrediction.status)
    )
    by_status = {row[0]: row[1] for row in by_status_q.all()}

    done = by_status.get("done", 0)
    pending = by_status.get("pending", 0)
    error = by_status.get("error", 0)
    persisted_total = done + pending + error
    missing = max(total - persisted_total, 0)

    return {
        "total_molecules": total,
        "done": done,
        "pending": pending,
        "error": error,
        "missing": missing,
    }


async def get_ids_needing_backfill(
    db: AsyncSession,
    limit: int,
    include_errors: bool = False,
) -> List[Tuple[UUID, str]]:
    """
    Return up to `limit` (molecule_id, smiles_canonical) tuples that still need
    ADMET predictions: either no admet_predictions row, or status='error' if
    include_errors=True. Excludes soft-deleted molecules and molecules with
    a null canonical SMILES.
    """
    needs_work = AdmetPrediction.id.is_(None)
    if include_errors:
        needs_work = needs_work | (AdmetPrediction.status == "error")

    stmt = (
        select(Molecule.id, Molecule.smiles_canonical)
        .outerjoin(AdmetPrediction, AdmetPrediction.id == Molecule.id)
        .where(
            Molecule._is_deleted.is_(False),
            Molecule.smiles_canonical.is_not(None),
            needs_work,
        )
        .order_by(Molecule.id)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def mark_done(
    db: AsyncSession,
    molecule_id: UUID,
    predictions: dict,
    model_version: str,
) -> None:
    """
    Mark a prediction row as done and store the predictions JSON + model version.
    """
    row = await get_by_id(db, molecule_id)
    if row is None:
        logger.warning(f"mark_done: no admet_predictions row for {molecule_id}")
        return
    row.status = "done"
    row.predictions = predictions
    row.model_version = model_version
    row.error = None


async def mark_error(db: AsyncSession, molecule_id: UUID, error: str) -> None:
    """
    Mark a prediction row as errored and store the error message.
    """
    row = await get_by_id(db, molecule_id)
    if row is None:
        logger.warning(f"mark_error: no admet_predictions row for {molecule_id}")
        return
    row.status = "error"
    row.error = error
