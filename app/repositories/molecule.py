from sqlalchemy import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.molecule import Molecule
from app.schemas.molecule import MoleculeCreate, MoleculeUpdate
from app.core.logging_config import logger
from fastapi import HTTPException
from app.utils.molecules import fp_gen
from app.utils.molecules.helper import standardize_smiles
import datamol as dm
from sqlalchemy.exc import IntegrityError


# Fetch a molecule by its ID from the database
async def get_molecule(db: AsyncSession, id: UUID):
    try:
        logger.info(f"Fetching molecule with ID: {id}")
        result = await db.execute(select(Molecule).filter(Molecule.id == id))
        db_molecule = result.scalar()
        if not db_molecule:
            logger.info(f"Molecule with ID {id} not found")
            return None
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with ID {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def get_molecule_by_smiles(db: AsyncSession, smiles_canonical: str):
    try:
        logger.info(f"Fetching molecule with SMILES : {smiles_canonical}")
        # standardize the smiles
        std_smiles_canonical = standardize_smiles(smiles_canonical)
        result = await db.execute(
            select(Molecule).filter(Molecule.smiles_canonical == std_smiles_canonical)
        )
        db_molecule = result.scalar()
        if not db_molecule:
            logger.info(f"Molecule with SMILES {smiles_canonical} not found")
            return None
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with SMILES {smiles_canonical}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Create a new molecule and commit it to the database
async def create_molecule(db: AsyncSession, molecule: MoleculeCreate):
    try:
        logger.info(f"Creating a new molecule with data: {molecule.model_dump()}")
        db_molecule = Molecule(**molecule.model_dump())

        # Mol
        db_molecule.mol = db_molecule.smiles_canonical
        # Fingerprints
        db_molecule.morgan_fp = fp_gen.generate_morgan_fp(db_molecule.mol)
        db_molecule.rdkit_fp = fp_gen.generate_rdkit_fp(db_molecule.mol)

        logger.debug(f"Inserting molecule: {db_molecule}")

        db.add(db_molecule)
        await db.commit()
        await db.refresh(db_molecule)
        logger.debug(f"Molecule created successfully: {db_molecule}")
        return db_molecule

    except IntegrityError as e:
        logger.error(f"Duplicate primary key error: {molecule.id} {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(
            status_code=400, detail="Molecule with this ID already exists."
        )

    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Update an existing molecule by its ID
async def update_molecule(db: AsyncSession, id: UUID, molecule: MoleculeUpdate):
    try:
        logger.info(f"Updating molecule with ID: {id}")
        db_molecule = await get_molecule(db, id)
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
        logger.error(f"Error updating molecule with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Delete a molecule by its ID
async def delete_molecule(db: AsyncSession, id: UUID):
    try:
        logger.info(f"Deleting molecule with ID: {id}")
        db_molecule = await get_molecule(db, id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        await db.delete(db_molecule)
        await db.commit()
        logger.info(f"Molecule with ID {id} deleted successfully")
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error deleting molecule with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
