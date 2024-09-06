import uuid
from app.repositories import molecule as molecule_repo
#from app.services.molecule.standardization import standardize_molecule
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.molecule_dto import InputMoleculeDto
from app.core.logging_config import logger
from app.services.molecule.standardization import standardize
from app.repositories.molecule import get_molecule_by_smiles_canonical

async def register(input_molecule: InputMoleculeDto, db: AsyncSession):
    """Handle standardization and creation of a molecule."""
    try:
        logger.info(f"Registering molecule: {input_molecule.model_dump()}")
        
        # Step 1: Standardize the molecule
        standardized_molecule = standardize(input_molecule)
        
        existing_molecule = await get_molecule_by_smiles_canonical(db, standardized_molecule.smiles_canonical)
        # Check if the molecule already exists in the database
        if existing_molecule:
            logger.info(f"Molecule already exists in the database: {existing_molecule}")
            return existing_molecule
        logger.info(f"Will create a new molecule: {standardized_molecule.smiles_canonical}")
        
        # Generate new GUID
        molecule_id = str(uuid.uuid4())
        standardized_molecule.id = molecule_id
        
        new_molecule = await molecule_repo.create_molecule(db, standardized_molecule)
        
        # Step 3: If not, create a new molecule
        # new_molecule = await molecule_repo.create_molecule(db, molecule.smiles, standardized_mol)
        # logger.debug(f"New molecule created: {new_molecule}")
      
        return standardized_molecule
        
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Error processing molecule: {e}")
        raise Exception("Internal error")
