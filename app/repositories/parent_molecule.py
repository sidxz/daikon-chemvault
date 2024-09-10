from sqlalchemy import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.parent_molecule import ParentMolecule
from app.schemas.parent_molecule import ParentMoleculeCreate, ParentMoleculeUpdate
from app.core.logging_config import logger
from fastapi import HTTPException
from app.utils.molecules import fp_gen
from app.utils.molecules.helper import standardize_smiles
import datamol as dm
from chembl_structure_pipeline import standardizer


# Fetch a parent molecule by its ID from the database
async def get_parent_molecule(db: AsyncSession, child_molblock: str) -> ParentMolecule:
    if not child_molblock:
        raise ValueError("Child molblock is required")

    try:
        logger.debug(f"Fetching parent molecule with molblock: {child_molblock}")

        parent_molblock, _ = standardizer.get_parent_molblock(child_molblock)
        parent_smiles = dm.to_smiles(dm.read_molblock(parent_molblock))

        result = await db.execute(
            select(ParentMolecule).filter(
                ParentMolecule.smiles_canonical == parent_smiles
            )
        )
        db_parent_molecule = result.scalar()
        if db_parent_molecule is None:
            logger.debug(f"ParentMolecule with molblock {child_molblock} not found")
            return None
        logger.debug(
            f"ParentMolecule fetched successfully: {db_parent_molecule}, SMILES: {parent_smiles}"
        )
        return db_parent_molecule
    except Exception as e:
        logger.error(
            f"Error fetching parent molecule with child molblock {child_molblock}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def get_parent_molecule_by_id(db: AsyncSession, id: UUID):
    try:
        logger.debug(f"Fetching ParentMolecule with ID: {id}")
        result = await db.execute(
            select(ParentMolecule).filter(ParentMolecule.id == id)
        )
        db_parent_molecule = result.scalar()
        if not db_parent_molecule:
            logger.info(f"ParentMolecule with ID {id} not found")
            return None
        logger.debug(f"ParentMolecule fetched successfully: {db_parent_molecule}")
        return db_parent_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with ID {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def get_parent_molecule_by_smiles(db: AsyncSession, smiles_canonical: str):
    try:
        logger.info(f"Fetching molecule with SMILES : {smiles_canonical}")
        # standardize the smiles
        std_smiles_canonical = standardize_smiles(smiles_canonical)
        result = await db.execute(
            select(ParentMolecule).filter(
                ParentMolecule.smiles_canonical == std_smiles_canonical
            )
        )
        db_parent_molecule = result.scalar()
        if not db_parent_molecule:
            logger.info(f"ParentMolecule with SMILES {smiles_canonical} not found")
            return None
        logger.debug(f"ParentMolecule fetched successfully: {db_parent_molecule}")
        return db_parent_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with SMILES {smiles_canonical}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Create a new molecule and commit it to the database
async def create_parent_molecule(db: AsyncSession, molecule: ParentMoleculeCreate):
    try:
        logger.debug(f"Creating a new ParentMolecule with data: {molecule.model_dump()}")
        db_parent_molecule = ParentMolecule(**molecule.model_dump())

        # Mol
        db_parent_molecule.mol = db_parent_molecule.smiles_canonical
        # Fingerprints
        db_parent_molecule.morgan_fp = fp_gen.generate_morgan_fp(db_parent_molecule.mol)
        db_parent_molecule.rdkit_fp = fp_gen.generate_rdkit_fp(db_parent_molecule.mol)

        db.add(db_parent_molecule)
        await db.commit()
        await db.refresh(db_parent_molecule)
        logger.debug(f"ParentMolecule created successfully: {db_parent_molecule}")
        return db_parent_molecule
    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Update an existing ParentMolecule by its ID
async def update_parent_molecule(
    db: AsyncSession, id: UUID, molecule: ParentMoleculeUpdate
):
    try:
        logger.info(f"Updating molecule with ID: {id}")
        db_parent_molecule = await get_parent_molecule(db, id)
        if not db_parent_molecule:
            raise HTTPException(status_code=404, detail="ParentMolecule not found")

        update_data = molecule.model_dump()
        for key, value in update_data.items():
            if hasattr(db_parent_molecule, key) and value is not None:
                setattr(db_parent_molecule, key, value)

        db.add(db_parent_molecule)
        await db.commit()
        await db.refresh(db_parent_molecule)
        logger.debug(f"ParentMolecule updated successfully: {db_parent_molecule}")
        return db_parent_molecule
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error updating ParentMolecule with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Delete a ParentMolecule by its ID
async def delete_parent_molecule(db: AsyncSession, id: UUID):
    try:
        logger.info(f"Deleting molecule with ID: {id}")
        db_parent_molecule = await get_parent_molecule(db, id)
        if not db_parent_molecule:
            raise HTTPException(status_code=404, detail="ParentMolecule not found")

        await db.delete(db_parent_molecule)
        await db.commit()
        logger.info(f"ParentMolecule with ID {id} deleted successfully")
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error Deleting ParentMolecule  with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")




async def bulk_create_parent_molecules(new_parent_molecules, db: AsyncSession):
    """
    Bulk create new parent molecules in the database.

    :param new_parent_molecules: List of parent molecules to be created.
    :param db: AsyncSession to interact with the database.
    """
    try:
        db.add_all(new_parent_molecules)
        await db.commit()
        logger.info(
            f"Successfully created {len(new_parent_molecules)} parent molecules."
        )
    except Exception as e:
        logger.error(f"Error during bulk parent molecule creation: {e}")
        await db.rollback()
        raise e


