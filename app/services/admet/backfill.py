import asyncio
import time
from typing import Optional

from app.core.logging_config import logger


async def run_backfill(
    chunk_size: int = 1000,
    limit: Optional[int] = None,
    include_errors: bool = False,
) -> None:
    """
    Background task: page through molecules that have no ADMET prediction row
    (or status='error' if include_errors=True), run ADMET in chunks, persist.

    Each chunk pattern: bulk_upsert_pending → predict_batch → mark_done/mark_error.
    After upsert_pending fires for a chunk, those rows no longer match the
    "needs work" filter, so the next page-fetch naturally skips them. This
    makes the loop self-paginating without OFFSET.
    """
    from app.db.base import SessionLocal
    from app.repositories import admet_prediction as repo
    from app.services.admet.predictor import predict_batch, get_model_version

    started = time.monotonic()
    processed_total = 0
    done_total = 0
    error_total = 0
    chunks = 0

    logger.info(
        f"ADMET backfill starting: chunk_size={chunk_size} limit={limit} "
        f"include_errors={include_errors}"
    )

    while True:
        remaining = None if limit is None else max(limit - processed_total, 0)
        if remaining is not None and remaining == 0:
            break
        page_size = chunk_size if remaining is None else min(chunk_size, remaining)

        async with SessionLocal() as db:
            items = await repo.get_ids_needing_backfill(
                db, limit=page_size, include_errors=include_errors
            )
            if not items:
                break
            await repo.bulk_upsert_pending(db, [mid for mid, _ in items])
            await db.commit()

        smiles = [s for _, s in items]
        try:
            results = await asyncio.to_thread(predict_batch, smiles)
        except Exception as e:
            logger.exception(f"ADMET backfill chunk {chunks + 1} failed during predict")
            async with SessionLocal() as db_err:
                for mid, _ in items:
                    await repo.mark_error(db_err, mid, str(e))
                await db_err.commit()
            error_total += len(items)
            processed_total += len(items)
            chunks += 1
            continue

        smi_to_props = dict(results)
        version = get_model_version()

        chunk_done = 0
        chunk_error = 0
        async with SessionLocal() as db:
            for mid, smi in items:
                props = smi_to_props.get(smi)
                if props is None:
                    await repo.mark_error(db, mid, "Invalid SMILES (rejected by admet_ai)")
                    chunk_error += 1
                else:
                    await repo.mark_done(db, mid, props, version)
                    chunk_done += 1
            await db.commit()

        done_total += chunk_done
        error_total += chunk_error
        processed_total += len(items)
        chunks += 1

        elapsed = time.monotonic() - started
        rate = processed_total / elapsed if elapsed > 0 else 0.0
        logger.info(
            f"ADMET backfill chunk {chunks}: +{chunk_done} done / +{chunk_error} error "
            f"(processed={processed_total}, elapsed={elapsed:.1f}s, rate={rate:.1f} mol/s)"
        )

    elapsed = time.monotonic() - started
    logger.info(
        f"ADMET backfill complete: processed={processed_total} done={done_total} "
        f"error={error_total} chunks={chunks} elapsed={elapsed:.1f}s"
    )
