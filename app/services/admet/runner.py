import asyncio
from typing import List, Tuple
from uuid import UUID

from app.core.logging_config import logger

# Cap the per-task batch size enqueued by inline registration triggers.
# Batch registration of N new molecules fans out to ceil(N / this) background tasks.
INLINE_TRIGGER_CHUNK_SIZE = 2000


async def run_admet_predictions(items: List[Tuple[UUID, str]]) -> None:
    """
    Background task: run admet_ai over (molecule_id, smiles) pairs and persist results.

    Owns its own DB session because the request-scoped session is already closed
    by the time FastAPI dispatches this task. Items whose SMILES admet_ai
    rejects (typically RDKit-unparseable) get a status="error" row so they
    don't get re-attempted on the next backfill pass.

    Self-sufficient: bulk-upserts pending rows up front so callers that haven't
    already done so (e.g. inline triggers from registration handlers) still get
    a row to update. Idempotent — calling bulk_upsert_pending twice is safe.
    """
    from app.db.base import SessionLocal
    from app.services.admet.predictor import predict_batch, get_model_version
    from app.repositories import admet_prediction as repo

    if not items:
        return

    async with SessionLocal() as db_init:
        try:
            await repo.bulk_upsert_pending(db_init, [mid for mid, _ in items])
            await db_init.commit()
        except Exception:
            logger.exception("ADMET runner: bulk_upsert_pending failed; aborting batch")
            return

    try:
        smiles = [s for _, s in items]
        # predict_batch is CPU-bound + blocking; offload off the event loop.
        results = await asyncio.to_thread(predict_batch, smiles)
        smi_to_props = dict(results)
        version = get_model_version()

        async with SessionLocal() as db:
            done_count = 0
            error_count = 0
            for mid, smi in items:
                props = smi_to_props.get(smi)
                if props is None:
                    await repo.mark_error(db, mid, "Invalid SMILES (rejected by admet_ai)")
                    error_count += 1
                else:
                    await repo.mark_done(db, mid, props, version)
                    done_count += 1
            await db.commit()

        logger.info(
            f"ADMET batch complete: {done_count} done, {error_count} invalid "
            f"(input={len(items)})"
        )
    except Exception as e:
        logger.exception("ADMET batch failed")
        try:
            async with SessionLocal() as db_err:
                for mid, _ in items:
                    await repo.mark_error(db_err, mid, str(e))
                await db_err.commit()
        except Exception:
            logger.exception("Failed to persist ADMET error state")
