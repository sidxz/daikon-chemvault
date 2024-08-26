from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.molecule import Molecule
from app.schemas.molecule import MoleculeCreate, MoleculeUpdate
from app.core.logging_config import logger
from fastapi import HTTPException


# Fetch a molecule by its ID from the database
async def get_molecule(db: AsyncSession, molecule_id: int):
    try:
        logger.info(f"Fetching molecule with ID: {molecule_id}")
        result = await db.execute(select(Molecule).filter(Molecule.id == molecule_id))
        db_molecule = result.scalar()
        if not db_molecule:
            logger.warning(f"Molecule with ID {molecule_id} not found")
            return None
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with ID {molecule_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Create a new molecule and commit it to the database
async def create_molecule(db: AsyncSession, molecule: MoleculeCreate):
    try:
        logger.info(f"Creating a new molecule with data: {molecule.model_dump()}")
        db_molecule = Molecule(**molecule.model_dump())
        db.add(db_molecule)
        await db.commit()
        await db.refresh(db_molecule)
        logger.debug(f"Molecule created successfully: {db_molecule}")
        return db_molecule
    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Update an existing molecule by its ID
async def update_molecule(db: AsyncSession, molecule_id: int, molecule: MoleculeUpdate):
    try:
        logger.info(f"Updating molecule with ID: {molecule_id}")
        db_molecule = await get_molecule(db, molecule_id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        update_data = molecule.model_dump()
        for key, value in update_data.items():
            if hasattr(db_molecule, key) and value is not None:
                setattr(db_molecule, key, value)

        db.add(db_molecule)
        await db.commit()
        await db.refresh(db_molecule)
        logger.debug(f"Molecule updated successfully: {db_molecule}")
        return db_molecule
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error updating molecule with ID {molecule_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Delete a molecule by its ID
async def delete_molecule(db: AsyncSession, molecule_id: int):
    try:
        logger.info(f"Deleting molecule with ID: {molecule_id}")
        db_molecule = await get_molecule(db, molecule_id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        await db.delete(db_molecule)
        await db.commit()
        logger.debug(f"Molecule with ID {molecule_id} deleted successfully")
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error deleting molecule with ID {molecule_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
