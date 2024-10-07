import uuid
from app.repositories import molecule as molecule_repo
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.parent_molecule import get_parent_molecule
from app.schemas.molecule import MoleculeUpdate
from app.schemas.molecule_dto import InputMoleculeDto
from app.core.logging_config import logger
from app.services.molecule.standardization import standardize, standardize_parent
from app.repositories.molecule import get_molecule_by_smiles
from app.repositories import parent_molecule as parent_molecule_repo


async def register(input_molecule: InputMoleculeDto, db: AsyncSession):
    """Handle standardization and creation of a molecule."""
    try:
        logger.info(f"Registering molecule: {input_molecule.model_dump()}")

        # Step 1: Standardize the molecule
        standardized_molecule = standardize(input_molecule)

        existing_molecule = await get_molecule_by_smiles(
            db, standardized_molecule.smiles_canonical
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
                return existing_molecule

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

        return standardized_molecule

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Error processing molecule: {e}")
        raise Exception("Internal error")


async def handle_molecule_name(
    existing_molecule, input_molecule_name: str, db: AsyncSession
):
    """Handle molecule name and synonyms if the name doesn't match or is not in synonyms."""
    if existing_molecule.name != input_molecule_name:

        # Ensure that the synonyms are split into a list
        existing_synonyms = (
            existing_molecule.synonyms.split(",") if existing_molecule.synonyms else []
        )

        # Add the input molecule name to the synonyms if it is not already present
        if input_molecule_name not in existing_synonyms:
            logger.info(
                f"Input name '{input_molecule_name}' not found in synonyms. Adding it."
            )
            existing_synonyms.append(input_molecule_name)
            # sort the synonyms
            existing_synonyms.sort()
            unique_synonyms = sorted(set(existing_synonyms))
            existing_molecule.synonyms = ",".join(unique_synonyms)

            # Update the molecule with the new synonyms
            update_molecule = MoleculeUpdate(
                id=existing_molecule.id,
                name=existing_molecule.name,
                synonyms=existing_molecule.synonyms
            )
            await molecule_repo.update_molecule(db, update_molecule.id, update_molecule)
    return existing_molecule
