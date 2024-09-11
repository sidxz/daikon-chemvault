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
    molecules_to_register = await filter_existing_molecules(standardized_molecules)

    if molecules_to_register:
        await bulk_insert_molecules(molecules_to_register)

    logger.info(f"Successfully processed {len(molecules_to_register)} molecules.")
    return molecules_to_register


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


async def filter_existing_molecules(standardized_molecules: List[Molecule]):
    logger.debug(f"Checking {len(standardized_molecules)} molecules in the database.")

    # Step 1: Extract all canonical SMILES from the standardized molecules
    smiles_list = [molecule.smiles_canonical for molecule in standardized_molecules]

    # Step 2: Perform a bulk query to find which SMILES already exist in the database
    existing_smiles = await get_existing_molecules_by_smiles(smiles_list)

    # Step 3: Filter out the molecules that exist in the database
    return [
        molecule
        for molecule in standardized_molecules
        if molecule.smiles_canonical not in existing_smiles
    ]


# Perform a bulk query to find which SMILES already exist in the database
async def get_existing_molecules_by_smiles(smiles_list: List[str]):
    """
    Query the database to find which canonical SMILES already exist in bulk.
    """
    async with semaphore:
        async for db in get_db():
            result = await db.execute(
                select(Molecule.smiles_canonical).where(
                    Molecule.smiles_canonical.in_(smiles_list)
                )
            )
            existing_smiles = result.scalars().all()
            return set(existing_smiles)


# Step 5: Bulk insert new molecules
async def bulk_insert_molecules(new_molecules: List[Molecule]):
    async with semaphore:
        async for db in get_db():
            await bulk_create_molecules(new_molecules, db)
