# import asyncio
# from typing import List, Dict, AsyncGenerator
# import uuid
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.logging_config import logger
# from app.db.models.molecule import Molecule
# from app.db.models.parent_molecule import ParentMolecule
# from app.repositories.molecule import (
#     bulk_create_molecules,
#     get_molecule_by_smiles,
# )
# from app.repositories.parent_molecule import (
#     bulk_create_parent_molecules,
#     get_parent_molecule,
# )
# from app.schemas.molecule_dto import InputMoleculeDto
# from app.services.molecule.standardization import standardize, standardize_parent
# from app.utils.molecules import fp_gen
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.asyncio import create_async_engine
# from app.core.config import settings


# semaphore = asyncio.Semaphore(30)

# # Async engine creation
# engine = create_async_engine(settings.CHEMVAULT_DATABASE_URL, pool_size=100, max_overflow=150)

# # Session generator with proper type hint
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with sessionmaker(
#         bind=engine, class_=AsyncSession, expire_on_commit=False
#     )() as session:
#         yield session


# async def register_molecules_batch(input_molecules: List[InputMoleculeDto]):
#     """
#     Register a batch of molecules after standardizing them. Avoids duplicate registrations by:
#     - Parallel standardization of molecules.
#     - Parallel parent molecule existence checks.
#     - Bulk creation of new parent molecules.
#     - Bulk creation of new molecules.
#     """
#     logger.info(f"Processing batch of {len(input_molecules)} molecules")

#     # Step 1: Parallel standardize molecules and check if they exist in the DB
#     standardized_molecules = await standardize_and_check_molecules(input_molecules)

#     # Step 2: Parallel check and find/create parent molecules for non-existing molecules
#     parent_molecule_map, new_parent_molecules = await find_or_prepare_parent_molecules(
#         standardized_molecules
#     )

#     # Step 3: Bulk create new parent molecules (if any)
#     if new_parent_molecules:
#         async for db in get_db():  # Use async for to fetch the session from the async generator
#             await bulk_create_parent_molecules(new_parent_molecules, db)

#     # Step 4: Link child molecules to their parent molecules, generate fingerprints, and bulk insert them
#     new_molecules = link_parent(standardized_molecules, parent_molecule_map)
#     if new_molecules:
#         async for db in get_db():  # Use async for to fetch the session from the async generator
#             await bulk_create_molecules(new_molecules, db)

#     logger.info(f"Successfully processed {len(new_molecules)} molecules.")
#     return new_molecules


# async def standardize_and_check_molecules(input_molecules: List[InputMoleculeDto]):
#     """
#     Parallelly standardize molecules and check in the database if they already exist.
#     Skip further processing for existing molecules.
#     """
#     logger.debug(f"Standardizing and checking {len(input_molecules)} molecules.")
#     tasks = [standardize_and_check_molecule(molecule) for molecule in input_molecules]
#     return [result for result in await asyncio.gather(*tasks) if result is not None]


# async def standardize_and_check_molecule(input_molecule: InputMoleculeDto):
#     """
#     Standardize a molecule, generate fingerprints, and check if it exists in the database.
#     If the molecule exists, skip it.
#     """
#     # Step 1: Standardize the molecule (unlimited concurrency)
#     standardized_molecule = standardize(input_molecule)

#     # Step 2: Check if the molecule already exists in the database (limited by semaphore)
#     async with semaphore:
#         async for db in get_db():  # Use async for to fetch the session from the async generator
#             if await molecule_exists(standardized_molecule.smiles_canonical, db):
#                 logger.debug(
#                     f"Molecule {standardized_molecule.smiles_canonical} already exists. Skipping."
#                 )
#                 return None

#     # Step 3: Create a Molecule object and generate fingerprints (unlimited concurrency)
#     standardized_molecule_db = Molecule(**standardized_molecule.model_dump())
#     try:
#         molecule_id = (
#             uuid.UUID(str(input_molecule.id))
#             if input_molecule.id is not None
#             else uuid.uuid4()
#         )
#     except ValueError:
#         logger.warning("Provided ID is not a valid UUID, generating a new one.")
#         molecule_id = uuid.uuid4()

#     standardized_molecule_db.id = molecule_id

#     # Step 4: Generate fingerprints
#     standardized_molecule_db.morgan_fp = fp_gen.generate_morgan_fp(
#         standardized_molecule.smiles_canonical
#     )
#     standardized_molecule_db.rdkit_fp = fp_gen.generate_rdkit_fp(
#         standardized_molecule.smiles_canonical
#     )

#     return standardized_molecule_db


# async def find_or_prepare_parent_molecules(standardized_molecules):
#     """
#     Parallelly find parent molecules in the database or prepare new ones for creation.
#     """
#     parent_molecule_map = {}
#     new_parent_molecules = []

#     tasks = [
#         find_or_create_parent_task(molecule, parent_molecule_map, new_parent_molecules)
#         for molecule in standardized_molecules
#     ]
#     await asyncio.gather(*tasks)

#     return parent_molecule_map, new_parent_molecules


# async def find_or_create_parent_task(
#     molecule, parent_molecule_map: Dict[str, uuid.UUID], new_parent_molecules: List
# ):
#     """
#     Find a parent molecule in the database, or prepare it for creation if it doesn't exist.
#     """
#     # Step 1: Check if the parent molecule exists in the database (limited by semaphore)
#     async with semaphore:
#         async for db in get_db():  # Use async for to fetch the session from the async generator
#             if molecule.o_molblock in parent_molecule_map:
#                 return

#             parent_molecule = await get_parent_molecule(db, molecule.o_molblock)

#             if parent_molecule:
#                 parent_molecule_map[molecule.o_molblock] = parent_molecule.id
#             else:
#                 # Step 2: Prepare a new parent molecule for creation (unlimited concurrency)
#                 new_parent = standardize_parent(molecule.o_molblock)
#                 new_parent_db = ParentMolecule(**new_parent.model_dump())
#                 new_parent_db.id = uuid.uuid4()  # Generate a new UUID for the parent
#                 new_parent_db.name = (
#                     molecule.name
#                 )  # Use the child molecule's name for the parent
#                 new_parent_db.morgan_fp = fp_gen.generate_morgan_fp(
#                     new_parent.smiles_canonical
#                 )
#                 new_parent_db.rdkit_fp = fp_gen.generate_rdkit_fp(
#                     new_parent.smiles_canonical
#                 )
#                 parent_molecule_map[molecule.o_molblock] = new_parent_db.id
#                 new_parent_molecules.append(new_parent_db)


# def link_parent(standardized_molecules, parent_molecule_map: Dict[str, uuid.UUID]):
#     """
#     Link standardized child molecules to their parent molecules using the parent_molecule_map.
#     """
#     for molecule in standardized_molecules:
#         molecule.parent_id = parent_molecule_map[molecule.o_molblock]

#     return standardized_molecules


# async def molecule_exists(smiles_canonical: str, db: AsyncSession) -> bool:
#     """
#     Check if a molecule with the given canonical SMILES already exists in the database.
#     """
#     existing_molecule = await get_molecule_by_smiles(db, smiles_canonical)
#     return existing_molecule is not None
