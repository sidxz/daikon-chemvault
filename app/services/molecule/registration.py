import uuid
from app.repositories import molecule as molecule_repo
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.parent_molecule import get_parent_molecule
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
        
        existing_molecule = await get_molecule_by_smiles(db, standardized_molecule.smiles_canonical)
        # Check if the molecule already exists in the database
        if existing_molecule:
            logger.info(f"Molecule already exists in the database: {existing_molecule}")
            return existing_molecule
        logger.info(f"Will create a new molecule: {standardized_molecule.smiles_canonical}")
        
        # Generate new GUID
        molecule_id = str(uuid.uuid4())
        standardized_molecule.id = molecule_id
        
        # Check for parent molecule
        parent_molecule = await get_parent_molecule(db, standardized_molecule.o_molblock)
        
        if parent_molecule:
            logger.info(f"Parent molecule found: {parent_molecule.smiles_canonical}")
            standardized_molecule.parent_id = parent_molecule.id
        else:
            # Register parent molecule
            logger.info("Parent molecule not found. Registering parent molecule.")
            parent_molecule_id = str(uuid.uuid4())
            standardized_parent_molecule = standardize_parent(standardized_molecule.o_molblock)
            standardized_parent_molecule.id = parent_molecule_id
            standardized_parent_molecule.name = input_molecule.name
            new_parent_molecule = await parent_molecule_repo.create_parent_molecule(db, standardized_parent_molecule)
            standardized_molecule.parent_id = new_parent_molecule.id
        
        
        new_molecule = await molecule_repo.create_molecule(db, standardized_molecule)
        
      
        return standardized_molecule
        
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Error processing molecule: {e}")
        raise Exception("Internal error")
