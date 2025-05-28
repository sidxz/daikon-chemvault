from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.base import SessionLocal
from app.repositories.molecule import get_all_molecules, get_molecules
from app.repositories import pains as pains_repo
from app.schemas.pains import PainsCreate
from app.core.logging_config import logger
from app.services.molcal.rd_pains import detect_pains

router = APIRouter()

# Dependency to get the database session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@router.post("/regenerate_pains_all", response_model=dict)
async def generate_pains_data(
    molecule_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate PAINS data for existing molecules.
    
    Args:
        molecule_ids (List[str], optional): List of molecule UUIDs to process. If not provided, all molecules are processed.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Success message with the number of processed molecules.
    """
    try:
        logger.info(f"Starting PAINS data generation for molecules.")

        # Step 1: Fetch molecules from the database
        if molecule_ids:
            molecules = await get_molecules(db, molecule_ids)
        else:
            molecules = await get_all_molecules(db)  # Fetch all molecules if no IDs provided

        if not molecules:
            logger.warning("No molecules found for PAINS processing.")
            raise HTTPException(status_code=404, detail="No molecules found.")

        logger.info(f"Fetched {len(molecules)} molecules for PAINS analysis.")

        # Step 2: Run PAINS detection in batch
        pains_results = detect_pains(molecules)

        # Step 3: Prepare PAINS data for bulk insertion
        pains_entries = [
            PainsCreate(
                id=molecule.id,
                rdkit_pains=result.rdkit_pains,
                rdkit_pains_label=result.rdkit_pains_label,
            )
            for molecule, result in zip(molecules, pains_results)
        ]

        # Step 4: Store PAINS results in the database
        if pains_entries:
            await pains_repo.bulk_create_pains(db, pains_entries)
            logger.info(f"PAINS data generated for {len(pains_entries)} molecules.")
        else:
            logger.info("No PAINS patterns detected.")

        return {"message": f"PAINS data generated for {len(pains_entries)} molecules."}

    except Exception as e:
        logger.error(f"Error during PAINS data generation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
