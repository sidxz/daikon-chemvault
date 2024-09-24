import asyncio
from typing import List, Dict, AsyncGenerator
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging_config import logger
from app.db.models.molecule import Molecule
from app.db.models.parent_molecule import ParentMolecule
from app.repositories.molecule import (
    bulk_create_molecules,
    get_molecule_by_smiles,
)
from app.repositories.parent_molecule import (
    bulk_create_parent_molecules,
    get_parent_molecule,
)
from app.schemas.molecule_dto import InputMoleculeDto
from app.services.molecule.standardization import standardize, standardize_parent
from app.utils.molecules import fp_gen
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from chembl_structure_pipeline import standardizer
import datamol as dm

semaphore = asyncio.Semaphore(30)

# Async engine creation
engine = create_async_engine(settings.DATABASE_URL, pool_size=100, max_overflow=150)


# Session generator with proper type hint
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session


async def register_molecules_batch(input_molecules: List[InputMoleculeDto]):
    """
    Register a batch of molecules after standardizing them. Avoids duplicate registrations by:
    - Parallel standardization of molecules.
    - Parallel parent molecule existence checks.
    - Bulk creation of new parent molecules.
    - Bulk creation of new molecules.
    """
    logger.info(f"Processing batch of {len(input_molecules)} molecules")

    # Step 1: Parallel standardize molecules and check if they exist in the DB
    standardized_molecules = await standardize_molecules(input_molecules)

    # Step 2: Consolidate duplicates within the standardized molecules list
    consolidated_molecules = consolidate_duplicates(standardized_molecules)

    # Step 3: Filter out existing molecules and update their synonyms
    molecules_to_update, molecules_to_register = await filter_existing_molecules(
        consolidated_molecules
    )

    # Step 4: Insert new molecules and update existing molecules
    if molecules_to_register:
        await bulk_insert_molecules(molecules_to_register)

    if molecules_to_update:
        await bulk_update_molecules(molecules_to_update)

    logger.info(
        f"Successfully registered {len(molecules_to_register)} molecules, updated {len(molecules_to_update)} molecules."
    )
    # Return combined array of updated and new molecules
    return molecules_to_register + molecules_to_update


# Step 1: Standardize molecules (without checking the DB yet)
async def standardize_molecules(input_molecules: List[InputMoleculeDto]):
    logger.debug(f"Standardizing {len(input_molecules)} molecules.")
    tasks = [standardize_molecule(molecule) for molecule in input_molecules]
    return await asyncio.gather(*tasks)


# Standardize individual molecule
async def standardize_molecule(input_molecule: InputMoleculeDto):
    """
    Standardize a molecule and generate fingerprints.
    """
    standardized_molecule = standardize(input_molecule)
    standardized_molecule_db = Molecule(**standardized_molecule.model_dump())
    try:
        molecule_id = (
            uuid.UUID(str(input_molecule.id))
            if input_molecule.id is not None
            else uuid.uuid4()
        )
    except ValueError:
        logger.warning("Provided ID is not a valid UUID, generating a new one.")
        molecule_id = uuid.uuid4()

    standardized_molecule_db.id = molecule_id
    standardized_molecule_db.morgan_fp = fp_gen.generate_morgan_fp(
        standardized_molecule.smiles_canonical
    )
    standardized_molecule_db.rdkit_fp = fp_gen.generate_rdkit_fp(
        standardized_molecule.smiles_canonical
    )
    standardized_molecule_db.mol = standardized_molecule.smiles_canonical
    return standardized_molecule_db


def consolidate_duplicates(standardized_molecules: List[Molecule]) -> List[Molecule]:
    """
    Consolidate molecules with the same canonical SMILES by combining their names into synonyms.
    """
    consolidated_molecule_dict = {}

    for molecule in standardized_molecules:
        if molecule.smiles_canonical in consolidated_molecule_dict:
            # If canonical SMILES already exists, combine names into synonyms
            existing_molecule = consolidated_molecule_dict[molecule.smiles_canonical]
            existing_molecule.synonyms = (
                existing_molecule.synonyms + ", " + molecule.name
                if existing_molecule.synonyms
                else molecule.name
            )
        else:
            # If it's a new canonical SMILES, add the molecule to the dictionary
            molecule.synonyms = molecule.name  # Set the initial synonym as the name
            consolidated_molecule_dict[molecule.smiles_canonical] = molecule

    # Return the list of consolidated molecules
    return list(consolidated_molecule_dict.values())


async def filter_existing_molecules(
    standardized_molecules: List[Molecule],
) -> List[Molecule]:
    logger.debug(f"Checking {len(standardized_molecules)} molecules in the database.")

    # Step 1: Extract all canonical SMILES from the standardized molecules
    smiles_list = [molecule.smiles_canonical for molecule in standardized_molecules]

    # Step 2: Perform a bulk query to find which SMILES already exist in the database
    existing_molecules = await get_existing_molecules_by_smiles(smiles_list)

    # Step 3: Update or create molecules
    updated_molecules = []
    new_molecules = []

    for molecule in standardized_molecules:
        existing_molecule = existing_molecules.get(molecule.smiles_canonical)

        if existing_molecule:
            # | is the union operator for sets
            existing_names_set = set(existing_molecule.synonyms.split(", ")) | {existing_molecule.name}
            new_names_set = set(molecule.synonyms.split(", ")) | {molecule.name}
            
            # Check
            if new_names_set.issubset(existing_names_set):
                continue

            existing_names_set.update(new_names_set)
            existing_names_set.discard(existing_molecule.name)
            
            # Sort and update the molecule's synonyms
            existing_molecule.synonyms = ", ".join(sorted(existing_names_set))
            
            updated_molecules.append(existing_molecule)
        else:
            # New molecule
            new_molecules.append(molecule)

    return updated_molecules, new_molecules


# Perform a bulk query to find which SMILES already exist in the database
async def get_existing_molecules_by_smiles(smiles_list: List[str]):
    """
    Query the database to find which canonical SMILES already exist in bulk.
    """
    async with semaphore:
        async for db in get_db():
            result = await db.execute(
                select(Molecule).where(Molecule.smiles_canonical.in_(smiles_list))
            )
            existing_molecules = result.scalars().all()
            return {
                molecule.smiles_canonical: molecule for molecule in existing_molecules
            }


# Step 5: Bulk insert new molecules
async def bulk_insert_molecules(new_molecules: List[Molecule]):
    async with semaphore:
        async for db in get_db():
            await bulk_create_molecules(new_molecules, db)


# Step 6 Bulk update existing molecules
BATCH_SIZE = 1000


async def bulk_update_molecules(updated_molecules: List[Molecule]):

    async with semaphore:
        async for db in get_db():
            try:
                for i in range(0, len(updated_molecules), BATCH_SIZE):
                    batch = updated_molecules[i : i + BATCH_SIZE]
                    logger.info(f"Updating batch of {len(batch)} molecules")

                    for molecule in batch:
                        # Use merge to reattach the object to the current session
                        logger.debug(f"Updating molecule {molecule}")
                        await db.merge(molecule)

                    await db.commit()
            except Exception as e:
                logger.error(f"Error updating molecules: {str(e)}")
                await db.rollback()
