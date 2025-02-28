from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.db.models.pains import Pains
from app.db.models.molecule import Molecule
from app.schemas.pains import PainsCreate, PainsRead, PainsUpdate
from app.core.logging_config import logger


async def get_pains_by_molecule_id(db: AsyncSession, molecule_id: str) -> Optional[PainsRead]:
    """
    Retrieve PAINS information for a given molecule ID.

    Args:
        db (AsyncSession): Database session.
        molecule_id (str): UUID of the molecule.

    Returns:
        PainsRead | None: PAINS details if found, otherwise None.
    """
    try:
        logger.info(f"Fetching PAINS data for Molecule ID: {molecule_id}")
        result = await db.execute(select(Pains).filter(Pains.id == molecule_id))
        db_pains = result.scalar()

        if not db_pains:
            logger.info(f"No PAINS data found for Molecule ID: {molecule_id}")
            return None

        return PainsRead(**db_pains.__dict__)  # Convert SQLAlchemy object to Pydantic model

    except Exception as e:
        logger.error(f"Error fetching PAINS for Molecule ID {molecule_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def get_pains_by_molecule_ids(db: AsyncSession, molecule_ids: List[str]) -> List[PainsRead]:
    """
    Retrieve PAINS data for multiple molecules by their IDs.

    Args:
        db (AsyncSession): Database session.
        molecule_ids (List[str]): List of molecule UUIDs.

    Returns:
        List[PainsRead]: List of PAINS records found.
    """
    try:
        logger.info(f"Fetching PAINS data for Molecule IDs: {molecule_ids}")
        result = await db.execute(select(Pains).filter(Pains.id.in_(molecule_ids)))
        db_pains_records = result.scalars().all()

        if not db_pains_records:
            logger.info(f"No PAINS data found for provided Molecule IDs.")
            return []

        return [PainsRead(**pains.__dict__) for pains in db_pains_records]

    except Exception as e:
        logger.error(f"Error fetching multiple PAINS records: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def create_pains(db: AsyncSession, pains_data: PainsCreate) -> PainsRead:
    """
    Insert PAINS detection results into the database.

    Args:
        db (AsyncSession): Database session.
        pains_data (PainsCreate): PAINS detection data.

    Returns:
        PainsRead: Newly created PAINS data.
    """
    try:
        # Ensure the molecule exists before inserting PAINS data
        result = await db.execute(select(Molecule).filter(Molecule.id == pains_data.id))
        molecule = result.scalar()

        if not molecule:
            raise HTTPException(status_code=404, detail=f"Molecule ID {pains_data.id} not found.")

        db_pains = Pains(**pains_data.model_dump())
        db.add(db_pains)
        await db.commit()
        await db.refresh(db_pains)

        logger.info(f"PAINS entry created for Molecule ID: {pains_data.id}")
        return PainsRead(**db_pains.__dict__)

    except IntegrityError:
        logger.error(f"PAINS entry already exists for Molecule ID: {pains_data.id}")
        await db.rollback()
        raise HTTPException(status_code=400, detail="PAINS entry already exists.")
    except Exception as e:
        logger.error(f"Error inserting PAINS data: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def update_pains(db: AsyncSession, molecule_id: str, pains_data: PainsUpdate) -> PainsRead:
    """
    Update an existing PAINS entry.

    Args:
        db (AsyncSession): Database session.
        molecule_id (str): UUID of the molecule.
        pains_data (PainsUpdate): Updated PAINS data.

    Returns:
        PainsRead: Updated PAINS data.
    """
    try:
        result = await db.execute(select(Pains).filter(Pains.id == molecule_id))
        db_pains = result.scalar()

        if not db_pains:
            raise HTTPException(status_code=404, detail="PAINS entry not found.")

        # Update only fields provided (non-None values)
        for key, value in pains_data.model_dump(exclude_unset=True).items():
            setattr(db_pains, key, value)

        await db.commit()
        await db.refresh(db_pains)

        logger.info(f"PAINS entry updated for Molecule ID: {molecule_id}")
        return PainsRead(**db_pains.__dict__)

    except Exception as e:
        logger.error(f"Error updating PAINS entry for Molecule ID {molecule_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def delete_pains_by_molecule_id(db: AsyncSession, molecule_id: str):
    """
    Delete PAINS information associated with a molecule.

    Args:
        db (AsyncSession): Database session.
        molecule_id (str): UUID of the molecule.

    Returns:
        None
    """
    try:
        result = await db.execute(select(Pains).filter(Pains.id == molecule_id))
        db_pains = result.scalar()

        if not db_pains:
            return None

        await db.delete(db_pains)
        await db.commit()
        logger.info(f"PAINS data deleted for Molecule ID: {molecule_id}")

    except Exception as e:
        logger.error(f"Error deleting PAINS entry for Molecule ID {molecule_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def bulk_create_pains(db: AsyncSession, pains_list: List[PainsCreate]):
    """
    Bulk insert PAINS detection results into the database.

    Args:
        db (AsyncSession): Database session.
        pains_list (List[PainsCreate]): List of PAINS detection results.
    """
    try:
        pains_entries = [Pains(**pains.model_dump()) for pains in pains_list]
        db.add_all(pains_entries)
        await db.commit()
        logger.info(f"Successfully inserted {len(pains_entries)} PAINS records.")

    except IntegrityError:
        logger.error("Integrity error: Some PAINS entries may already exist.")
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate PAINS entry detected.")
    except Exception as e:
        logger.error(f"Error inserting PAINS records: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def bulk_delete_pains(db: AsyncSession, molecule_ids: List[str]):
    """
    Bulk delete PAINS data for multiple molecules.

    Args:
        db (AsyncSession): Database session.
        molecule_ids (List[str]): List of molecule IDs to delete PAINS results for.
    """
    try:
        result = await db.execute(select(Pains).filter(Pains.id.in_(molecule_ids)))
        pains_records = result.scalars().all()

        if not pains_records:
            return

        for record in pains_records:
            await db.delete(record)

        await db.commit()
        logger.info(f"PAINS data deleted for {len(pains_records)} molecules.")

    except Exception as e:
        logger.error(f"Error during bulk PAINS deletion: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
