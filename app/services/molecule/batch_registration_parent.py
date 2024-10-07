import asyncio
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, AsyncGenerator
from app.core.config import settings
from app.db.models.molecule import Molecule
from app.core.logging_config import logger
from chembl_structure_pipeline import standardizer
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models.parent_molecule import ParentMolecule
from app.services.molecule.standardization import standardize_parent
from dotenv import load_dotenv
from sqlalchemy import update, case

from app.utils.molecules import fp_gen

# Configurable batch size for molecule processing
BATCH_SIZE = 1000

load_dotenv()

# Create an async engine for database operations
engine = create_async_engine(settings.CHEMVAULT_DATABASE_URL, pool_size=100, max_overflow=150)

# Database session generator
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session


# Fetch a batch of molecules that do not have a parent_id
async def fetch_molecule_batch_without_parents(offset: int, limit: int) -> List[Molecule]:
    logger.info(f"Fetching molecules without parent from offset: {offset}, limit: {limit}")
    async with sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)() as db:
        try:
            result = await db.execute(
                select(Molecule).where(Molecule.parent_id == None).offset(offset).limit(limit)
            )
            molecules = result.scalars().all()
            logger.info(f"Fetched {len(molecules)} molecules without parents.")
            return molecules
        except Exception as e:
            logger.error(f"Error fetching molecules: {e}")
            raise


# Insert new parent molecules into the database
async def insert_new_parents(parents_to_create: List[ParentMolecule], db: AsyncSession):
    if parents_to_create:
        logger.info(f"Preparing to insert {len(parents_to_create)} new parent molecules.")
        try:
            parent_molecules = []
            for parent in parents_to_create:
                db_parent_molecule = ParentMolecule(**parent.model_dump())
                db_parent_molecule.mol = db_parent_molecule.smiles_canonical
                # Generate Fingerprints
                db_parent_molecule.morgan_fp = fp_gen.generate_morgan_fp(db_parent_molecule.mol)
                db_parent_molecule.rdkit_fp = fp_gen.generate_rdkit_fp(db_parent_molecule.mol)
                parent_molecules.append(db_parent_molecule)

            db.add_all(parent_molecules)
            await db.commit()
            logger.info(f"Successfully inserted {len(parent_molecules)} parent molecules.")
        except Exception as e:
            logger.error(f"Error inserting parent molecules: {e}")
            raise


# Update molecules in bulk with the assigned parent_id
async def bulk_update_molecule_parents(update_mappings: List[Dict[str, uuid.UUID]], db: AsyncSession):
    if update_mappings:
        logger.info(f"Preparing to update {len(update_mappings)} molecules with parent IDs.")
        try:
            case_conditions = [
                (Molecule.id == mapping["id"], mapping["parent_id"])
                for mapping in update_mappings
            ]

            await db.execute(
                update(Molecule)
                .where(Molecule.id.in_([mapping["id"] for mapping in update_mappings]))
                .values(
                    parent_id=(
                        case(
                            *case_conditions,
                            else_=Molecule.parent_id,
                        )
                    )
                )
            )
            await db.commit()
            logger.info(f"Successfully updated {len(update_mappings)} molecules with parent IDs.")
        except Exception as e:
            logger.error(f"Error updating molecules: {e}")
            raise


# Process a batch of molecules to standardize parents, link or create them
async def process_molecule_parents(molecules: List[Molecule], db: AsyncSession):
    logger.info(f"Processing {len(molecules)} molecules for parent assignment.")
    try:
        # Standardize parents for all molecules and create a mapping (id -> standardized parent)
        parent_map = {mol.id: standardize_parent(mol.o_molblock) for mol in molecules}
        parent_smiles = [parent.smiles_canonical for parent in parent_map.values()]

        # Fetch existing parents from the database using their canonical SMILES
        existing_parents = await fetch_existing_parents_by_smiles(parent_smiles, db)

        update_mappings, parents_to_create = [], []
        for molecule in molecules:
            parent = parent_map[molecule.id]

            # If parent already exists, assign parent_id to molecule
            if parent.smiles_canonical in existing_parents:
                molecule.parent_id = existing_parents[parent.smiles_canonical].id
            else:
                # If parent doesn't exist, create a new parent entry
                if not any(p.smiles_canonical == parent.smiles_canonical for p in parents_to_create):
                    parent.id = uuid.uuid4()
                    parent.name = molecule.name
                    parents_to_create.append(parent)
                molecule.parent_id = next(p.id for p in parents_to_create if p.smiles_canonical == parent.smiles_canonical)

            update_mappings.append({"id": molecule.id, "parent_id": molecule.parent_id})

        # Insert new parent molecules and update molecules in bulk
        await insert_new_parents(parents_to_create, db)
        await bulk_update_molecule_parents(update_mappings, db)
        logger.info(f"Successfully processed {len(molecules)} molecules.")
    except Exception as e:
        logger.error(f"Error processing molecules: {e}")
        raise


# Fetch existing parent molecules by canonical SMILES in bulk
async def fetch_existing_parents_by_smiles(smiles_list: List[str], db: AsyncSession) -> Dict[str, ParentMolecule]:
    logger.info(f"Fetching existing parents for {len(smiles_list)} canonical SMILES.")
    try:
        result = await db.execute(
            select(ParentMolecule).where(ParentMolecule.smiles_canonical.in_(smiles_list))
        )
        existing_parents = {parent.smiles_canonical: parent for parent in result.scalars().all()}
        logger.info(f"Fetched {len(existing_parents)} existing parent molecules.")
        return existing_parents
    except Exception as e:
        logger.error(f"Error fetching existing parents: {e}")
        raise


# Process all molecules in batches
async def process_all_molecule_batches():
    offset = 0
    logger.info("Starting the batch process for molecule parents.")
    while True:
        # Fetch a batch of molecules without parent_id
        molecules = await fetch_molecule_batch_without_parents(offset, BATCH_SIZE)
        if not molecules:
            logger.info("No more molecules to process. Exiting.")
            break

        # Process the current batch to standardize and assign parents
        async with sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)() as db:
            await process_molecule_parents(molecules, db)

        offset += BATCH_SIZE
        logger.info(f"Processed batch with offset {offset - BATCH_SIZE} to {offset}.")


# Main entry point for processing molecules
# if __name__ == "__main__":
# asyncio.run(process_all_molecule_batches())
