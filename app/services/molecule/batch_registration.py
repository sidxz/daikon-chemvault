import asyncio
from typing import List, Dict, AsyncGenerator, Tuple
from uuid import UUID
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging_config import logger
from app.db.models.molecule import Molecule
from app.db.models.parent_molecule import ParentMolecule
from app.repositories.molecule import (
    bulk_create_molecules,
    get_molecule_by_smiles,
    get_molecules_by_name_exact,
)
from app.repositories.parent_molecule import (
    bulk_create_parent_molecules,
    get_parent_molecule,
)
from app.schemas.molecule_dto import InputMoleculeDto
from app.schemas.pains import PainsCreate
from app.services.molcal.rd_pains import detect_pains
from app.services.molecule.standardization import standardize, standardize_parent
from app.utils.molecules import fp_gen
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from chembl_structure_pipeline import standardizer
import datamol as dm
import re
from app.repositories import pains as pains_repo
from app.services.molecule.registration_helpers import _name_key, _split_synonyms_csv
from app.schemas.molecule import MoleculeBase

semaphore = asyncio.Semaphore(30)

# Async engine creation
engine = create_async_engine(settings.DATABASE_URL, pool_size=100, max_overflow=150)


# Session generator with proper type hint
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session


def validate_input_molecules(
    input_molecules: List[InputMoleculeDto],
) -> List[InputMoleculeDto]:
    """
    Validate and clean up input molecules by:
    1. Removing newline characters and trailing spaces from the name.
    2. Removing trailing spaces and unexpected characters from the SMILES string.
    3. Converting the SMILES string to a molecule; if it fails, removing the entry from the list.
    """
    valid_molecules = []
    # Allow common SMILES characters: alphanumerics, specific symbols, and brackets
    allowed_chars = re.compile(r"[^A-Za-z0-9@+\-\[\]\(\)=#$%^.&*!:;]")

    for molecule in input_molecules:
        # Clean up the name
        molecule.name = molecule.name.strip().replace("\n", "").replace("\r", "")

        # Clean up the SMILES string: remove trailing spaces and unexpected characters
        molecule.smiles = molecule.smiles.strip()
        molecule.smiles = re.sub(allowed_chars, "", molecule.smiles)

        # Try to convert SMILES to a molecule
        rdkit_mol = dm.to_mol(molecule.smiles)
        if rdkit_mol is None:
            logger.warning(
                f"Invalid SMILES after cleaning: {molecule.smiles}. Skipping molecule."
            )
            continue

        valid_molecules.append(molecule)

    logger.info(
        f"Validated {len(valid_molecules)} molecules out of {len(input_molecules)}."
    )
    return valid_molecules


async def filter_conflicting_name_structure(
    standardized_molecules: List[Molecule], db: AsyncSession
) -> List[Molecule]:
    """
    Enforce:
      - Within the batch: same normalized name -> same smiles_canonical.
      - Vs DB: if a name (as primary or synonym) already exists, it must map
        to the same smiles_canonical.

    Conflicting molecules are SKIPPED (logged), not causing the whole batch to fail.
    """
    filtered: list[Molecule] = []
    name_to_smiles_batch: dict[str, str] = {}
    name_to_display: dict[str, str] = {}

    # -----------------------------
    # 1) Intra-batch consistency
    # -----------------------------
    for m in standardized_molecules:
        if m is None:
            continue

        key = _name_key(m.name)
        if not key:
            # No name -> can't do name-based checks; still keep it
            filtered.append(m)
            continue

        smi = m.smiles_canonical
        if key in name_to_smiles_batch:
            if name_to_smiles_batch[key] != smi:
                logger.warning(
                    f"Skipping molecule '{m.name}' in batch: name maps to multiple "
                    f"structures ({name_to_smiles_batch[key]} vs {smi})."
                )
                continue  # skip conflicting batch entry
        else:
            name_to_smiles_batch[key] = smi
            name_to_display[key] = m.name.strip()

        filtered.append(m)

    if not name_to_smiles_batch:
        return filtered

    # -----------------------------
    # 2) Consistency vs DB (names and synonyms)
    # -----------------------------
    # Use original display names for lookup (so get_molecules_by_name_exact can
    # match on primary name or synonyms)
    names_for_lookup = list({v for v in name_to_display.values() if v})
    existing = await get_molecules_by_name_exact(db, names_for_lookup)
    if not existing:
        return filtered

    # Build a map: normalized_name_key -> smiles_canonical (from DB),
    # using BOTH mol.name and each synonym token.
    db_name_to_smi: dict[str, str] = {}

    for mol in existing:
        # Collect all names this molecule claims: primary + synonyms
        all_names: list[str] = []
        if mol.name:
            all_names.append(mol.name)
        all_names.extend(_split_synonyms_csv(mol.synonyms))

        for raw_name in all_names:
            key = _name_key(raw_name)
            if not key:
                continue

            if key in db_name_to_smi and db_name_to_smi[key] != mol.smiles_canonical:
                # Your DB is already inconsistent (same name -> multiple structures).
                # Log and keep the first mapping; we still use this for conflict checks.
                logger.error(
                    "Name '%s' in DB already maps to multiple structures: %s vs %s. "
                    "Using the first one for conflict checks.",
                    raw_name,
                    db_name_to_smi[key],
                    mol.smiles_canonical,
                )
                continue

            db_name_to_smi.setdefault(key, mol.smiles_canonical)

    # Now drop batch molecules whose name would conflict with an existing DB mapping
    final: list[Molecule] = []
    for m in filtered:
        key = _name_key(m.name)
        if not key or key not in db_name_to_smi:
            final.append(m)
            continue

        batch_smi = m.smiles_canonical
        db_smi = db_name_to_smi[key]

        if db_smi != batch_smi:
            logger.warning(
                "Skipping molecule '%s' in batch: name already exists in DB for a "
                "different structure (%s vs %s).",
                m.name,
                db_smi,
                batch_smi,
            )
            continue  # skip conflicting entry

        final.append(m)

    return final


async def register_molecules_batch(
    input_molecules: List[InputMoleculeDto], preview_mode: bool = False
) -> Tuple[list, List[Tuple[UUID, str]]]:
    """
    Register a batch of molecules:
    1. Standardize molecules.
    2. Enforce name–structure consistency.
    3. Consolidate duplicates within the batch.
    4. Check against existing molecules in the database.
    5. Bulk insert new molecules.
    6. Bulk update existing molecules with new synonyms.
    7. Perform PAINS detection on newly registered molecules.

    Returns (combined_response, newly_created), where:
      - combined_response is the same union of registered + updated + unchanged
        molecules that callers expect (or the preview-mode equivalent),
      - newly_created is [(id, smiles_canonical), …] for molecules that were
        actually inserted in this call. Empty in preview mode, on early return,
        and on exception paths. Handlers use this to gate ADMET side effects.
    """

    logger.info(
        f"Received batch of {len(input_molecules)} molecules with preview mode set to {preview_mode}."
    )

    validated_molecules = validate_input_molecules(input_molecules)
    if not validated_molecules:
        logger.warning("No valid molecules found after validation.")
        return [], []

    async for db in get_db():
        try:
            standardized_molecules = await standardize_molecules(validated_molecules)
            standardized_molecules = [
                m for m in standardized_molecules if m is not None
            ]

            # NEW: enforce name–structure consistency; skip conflicts
            standardized_molecules = await filter_conflicting_name_structure(
                standardized_molecules, db
            )
            consolidated_molecules = consolidate_duplicates(standardized_molecules)

            molecules_to_update, molecules_to_register, not_changed_molecules = (
                await filter_existing_molecules(consolidated_molecules, db)
            )

            if preview_mode:
                logger.info(
                    f"Preview mode: {len(molecules_to_register)} molecules would be registered, "
                    f"{len(molecules_to_update)} molecules would be updated."
                )
                preview_results = (
                    molecules_to_register + molecules_to_update + not_changed_molecules
                )
                orm_detached_payload = [
                    MoleculeBase.model_validate(m, from_attributes=True)
                    for m in preview_results
                ]
                await db.rollback()  # important: clears dirty state
                return orm_detached_payload, []

            if molecules_to_register and not preview_mode:
                await bulk_insert_molecules(molecules_to_register, db)
                await perform_pains_detection(molecules_to_register, db)

            if molecules_to_update and not preview_mode:
                await bulk_update_molecules(molecules_to_update, db)

            logger.info(
                f"Successfully registered {len(molecules_to_register)} molecules, "
                f"updated {len(molecules_to_update)} molecules."
            )
            newly_created = [
                (m.id, m.smiles_canonical)
                for m in molecules_to_register
                if m.smiles_canonical
            ]
            return (
                molecules_to_register + molecules_to_update + not_changed_molecules,
                newly_created,
            )

        except Exception as e:
            logger.error(f"Unexpected error in molecule registration: {e}")
            await db.rollback()
            return [], []


async def perform_pains_detection(molecules: List[Molecule], db: AsyncSession):
    """
    Perform PAINS detection on newly registered molecules and save the results.
    """
    if not molecules:
        return

    logger.info(f"Performing PAINS detection for {len(molecules)} molecules.")

    try:
        pains_results = detect_pains(molecules)

        if pains_results:
            pains_entries = [
                PainsCreate(
                    id=molecule.id,
                    rdkit_pains=result.rdkit_pains,
                    rdkit_pains_label=result.rdkit_pains_label,
                )
                for molecule, result in zip(molecules, pains_results)
            ]

            await pains_repo.bulk_create_pains(db=db, pains_list=pains_entries)
            logger.info(
                f"PAINS detection completed for {len(pains_entries)} molecules."
            )

    except Exception as e:
        logger.error(f"Error during PAINS detection: {e}")


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
    try:
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

    except Exception as e:
        logger.error(f"Error standardizing molecule: {str(e)}. Skipping this molecule.")
        return None


def consolidate_duplicates(standardized_molecules: List[Molecule]) -> List[Molecule]:
    """
    Consolidate molecules with the same canonical SMILES by combining their names into synonyms.
    Synonyms are stored as CSV without spaces, deduped using the normalized key.
    """
    consolidated_molecule_dict: dict[str, Molecule] = {}

    for molecule in standardized_molecules:
        if molecule is None:
            continue

        smi = molecule.smiles_canonical
        primary_name = (molecule.name or "").strip()

        if smi in consolidated_molecule_dict:
            existing = consolidated_molecule_dict[smi]

            # Build key->display map for synonyms
            syn_map: dict[str, str] = {}
            for s in _split_synonyms_csv(existing.synonyms):
                syn_map.setdefault(_name_key(s), s)

            # Add incoming name as synonym if different
            key = _name_key(primary_name)
            if key and key != _name_key(existing.name):
                syn_map.setdefault(key, primary_name)

            # Canonical storage: sorted, no spaces
            existing.synonyms = ",".join(sorted(syn_map.values()))
        else:
            molecule.name = primary_name
            # Initial synonyms = just this name (not normalized in display, but key is)
            key = _name_key(primary_name)
            syn_map = {}
            if key:
                syn_map[key] = primary_name
            molecule.synonyms = ",".join(sorted(syn_map.values()))
            consolidated_molecule_dict[smi] = molecule

    return list(consolidated_molecule_dict.values())


async def filter_existing_molecules(
    standardized_molecules: List[Molecule], db: AsyncSession
):
    logger.debug(f"Checking {len(standardized_molecules)} molecules in the database.")

    smiles_list = [molecule.smiles_canonical for molecule in standardized_molecules]
    existing_molecules = await get_existing_molecules_by_smiles(smiles_list, db)

    updated_molecules: list[Molecule] = []
    new_molecules: list[Molecule] = []
    not_changed_molecules: list[Molecule] = []

    for molecule in standardized_molecules:
        existing_molecule = existing_molecules.get(molecule.smiles_canonical)

        if existing_molecule:
            # Build sets of names (including primary name) from both sides
            existing_names = set(_split_synonyms_csv(existing_molecule.synonyms))
            existing_names.add((existing_molecule.name or "").strip())

            new_names = set(_split_synonyms_csv(molecule.synonyms))
            new_names.add((molecule.name or "").strip())

            # Normalize for comparison (same key as lookup)
            existing_keys = {_name_key(n) for n in existing_names if n}
            new_keys = {_name_key(n) for n in new_names if n}

            if new_keys.issubset(existing_keys):
                # Nothing new to add
                not_changed_molecules.append(existing_molecule)
                continue

            # Merge sets but keep primary name out of synonyms
            merged_display: dict[str, str] = {}

            for n in existing_names | new_names:
                if not n:
                    continue
                key = _name_key(n)
                if key and key != _name_key(existing_molecule.name):
                    merged_display.setdefault(key, n)

            existing_molecule.synonyms = ",".join(sorted(merged_display.values()))
            updated_molecules.append(existing_molecule)
        else:
            new_molecules.append(molecule)

    return updated_molecules, new_molecules, not_changed_molecules


# Perform a bulk query to find which SMILES already exist in the database
async def get_existing_molecules_by_smiles(smiles_list: List[str], db: AsyncSession):
    """
    Query the database to find which canonical SMILES already exist in bulk.
    """
    result = await db.execute(
        select(Molecule).where(Molecule.smiles_canonical.in_(smiles_list))
    )
    existing_molecules = result.scalars().all()
    return {molecule.smiles_canonical: molecule for molecule in existing_molecules}


# Step 5: Bulk insert new molecules
async def bulk_insert_molecules(new_molecules: List[Molecule], db: AsyncSession):
    await bulk_create_molecules(new_molecules, db)


# Step 6 Bulk update existing molecules
BATCH_SIZE = 1000


async def bulk_update_molecules(updated_molecules: List[Molecule], db: AsyncSession):
    try:
        for i in range(0, len(updated_molecules), BATCH_SIZE):
            batch = updated_molecules[i : i + BATCH_SIZE]
            logger.info(f"Updating batch of {len(batch)} molecules")

            for molecule in batch:
                logger.debug(f"Updating molecule {molecule}")
                await db.merge(molecule)

            await db.commit()

    except Exception as e:
        logger.error(f"Error updating molecules: {str(e)}")
        await db.rollback()
