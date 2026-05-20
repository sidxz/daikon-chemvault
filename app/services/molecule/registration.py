import uuid
from typing import Tuple
from app.repositories import molecule as molecule_repo
from app.repositories import pains as pains_repo

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.parent_molecule import get_parent_molecule
from app.schemas.molecule import MoleculeUpdate
from app.schemas.molecule_dto import InputMoleculeDto
from app.core.logging_config import logger
from app.schemas.pains import PainsCreate
from app.services.molcal.rd_pains import detect_pains
from app.services.molecule.standardization import standardize, standardize_parent
from app.repositories.molecule import get_molecule_by_smiles
from app.repositories import parent_molecule as parent_molecule_repo


async def register(input_molecule: InputMoleculeDto, db: AsyncSession) -> Tuple[object, bool]:
    """Handle standardization and creation of a molecule.

    Returns (molecule, is_new) where is_new is True only when a new row was
    actually inserted. Callers use is_new to gate post-create side effects
    such as ADMET prediction; existing-molecule lookups (even those that
    merge synonyms) return is_new=False.
    """
    try:
        logger.info(f"Registering molecule: {input_molecule.model_dump()}")

        # Step 1: Standardize the molecule
        standardized_molecule = standardize(input_molecule)

        # Check name uniqueness
        existing_molecule_by_name = await molecule_repo.get_molecule_by_name_exact(
            db, input_molecule.name
        )
        existing_molecule = await get_molecule_by_smiles(
            db, standardized_molecule.smiles_canonical
        )

        # [New] Reject if name is same but smiles_canonical is different
        if existing_molecule_by_name and (
            not existing_molecule
            or existing_molecule.id != existing_molecule_by_name.id
        ):
            logger.error(
                f"Molecule name conflict: {input_molecule.name} already exists with different structure."
            )
            raise ValueError(
                f"Molecule name '{input_molecule.name}' already exists with a different structure."
            )

        # Check if the molecule already exists in the database
        if existing_molecule:
            logger.info(f"Molecule already exists in the database: {existing_molecule}")
            try:
                existing_molecule = await handle_molecule_name(
                    existing_molecule, input_molecule.name, db
                )
            except Exception as e:
                logger.error(f"Error handling molecule name: {e}")
                raise Exception("Internal error")
            finally:
                return existing_molecule, False

        logger.info(
            f"Will create a new molecule: {standardized_molecule.smiles_canonical}"
        )

        # Check if input_molecule.id is present and is a valid UUID, then use it else generate a new one
        try:
            molecule_id = (
                uuid.UUID(str(input_molecule.id))
                if input_molecule.id is not None
                else uuid.uuid4()
            )
        except ValueError:
            # Handle case where provided ID is not a valid UUID
            logger.warning("Provided ID is not a valid UUID, generating a new one.")
            molecule_id = uuid.uuid4()

        standardized_molecule.id = molecule_id

        # Check for parent molecule
        parent_molecule = await get_parent_molecule(
            db, standardized_molecule.o_molblock
        )

        if parent_molecule:
            logger.info(f"Parent molecule found: {parent_molecule.smiles_canonical}")
            standardized_molecule.parent_id = parent_molecule.id
        else:
            # Register parent molecule
            logger.info("Parent molecule not found. Registering parent molecule.")
            parent_molecule_id = str(uuid.uuid4())
            standardized_parent_molecule = standardize_parent(
                standardized_molecule.o_molblock
            )
            standardized_parent_molecule.id = parent_molecule_id
            standardized_parent_molecule.name = input_molecule.name
            new_parent_molecule = await parent_molecule_repo.create_parent_molecule(
                db, standardized_parent_molecule
            )
            standardized_molecule.parent_id = new_parent_molecule.id

        new_molecule = await molecule_repo.create_molecule(db, standardized_molecule)

        # Step 4: Check for PAINS and store results
        try:
            pains_results = detect_pains(
                [standardized_molecule]
            )  # Call PAINS detection
            if pains_results:
                pains_entry = PainsCreate(
                    id=standardized_molecule.id,
                    rdkit_pains=pains_results[0].rdkit_pains,
                    rdkit_pains_label=pains_results[0].rdkit_pains_label,
                )
                await pains_repo.create_pains(db, pains_entry)  # Save PAINS result
                logger.info(f"PAINS detection completed for Molecule ID: {molecule_id}")
            else:
                logger.info(f"No PAINS detected for Molecule ID: {molecule_id}")
        except Exception as e:
            logger.error(
                f"Error during PAINS detection for Molecule ID {molecule_id}: {e}"
            )

        return standardized_molecule, True

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Error processing molecule: {e}")
        raise Exception("Internal error")

def _syn_key(s: str) -> str:
    # same as query: strip, lower, remove all spaces
    return s.strip().lower().replace(" ", "")

async def handle_molecule_name(
    existing_molecule, input_molecule_name: str, db: AsyncSession
):
    """Handle molecule name and synonyms if the name doesn't match or is not in synonyms."""
    if not input_molecule_name:
        return existing_molecule

    raw_input = input_molecule_name
    input_name_norm = raw_input.strip()
    input_key = _syn_key(raw_input)

    # If the *existing* primary name matches under the same normalization, do nothing
    if existing_molecule.name:
        if _syn_key(existing_molecule.name) == input_key:
            return existing_molecule

    # Build a map of normalized_key -> original_token for synonyms
    syn_map = {}

    if existing_molecule.synonyms:
        raw_synonyms = existing_molecule.synonyms.split(",")
        for s in raw_synonyms:
            s_clean = s.strip()
            if not s_clean:
                continue
            key = _syn_key(s_clean)
            # keep first encountered representation
            syn_map.setdefault(key, s_clean)

    # If this name (under normalized key) is not already a synonym, add it
    if input_key not in syn_map:
        logger.info(
            f"Input name '{input_molecule_name}' not found in synonyms. Adding it."
        )
        syn_map[input_key] = input_name_norm

        # Canonical storage: sort by display token, join with commas (no spaces)
        new_synonyms_sorted = sorted(syn_map.values())
        existing_molecule.synonyms = ",".join(new_synonyms_sorted)

        update_molecule = MoleculeUpdate(
            id=existing_molecule.id,
            name=existing_molecule.name,
            synonyms=existing_molecule.synonyms,
        )
        await molecule_repo.update_molecule(db, update_molecule.id, update_molecule)

    return existing_molecule
