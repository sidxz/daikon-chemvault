from app.schemas.molecule_dto import InputMoleculeDto
from app.schemas.molecule import MoleculeBase
import datamol as dm
from chembl_structure_pipeline import standardizer
from app.core.logging_config import logger
from app.utils.molecules.compliance import Ro5


def standardize(input_molecule: InputMoleculeDto) -> MoleculeBase:
    """Standardizes a molecule and computes molecular descriptors.

    Args:
        input_molecule (InputMoleculeDto): Input molecule data.

    Returns:
        MoleculeBase: Standardized molecule with computed descriptors and RO5 compliance.

    Raises:
        ValueError: If the input molecule data is invalid.
        Exception: For other internal processing errors.
    """
    logger.debug(f"Standardizing molecule: {input_molecule.model_dump()}")

    try:
        # Initialize molecule object from input DTO
        molecule = MoleculeBase(**input_molecule.model_dump())

        # Convert SMILES to RDKit mol object
        mol = dm.to_mol(molecule.smiles)
        if not mol:
            raise ValueError(f"Unable to convert SMILES to mol: {molecule.smiles}")
        
        # Generate original molblock and standardize it
        molecule.o_molblock = dm.to_molblock(mol)
        molecule.std_molblock = standardizer.standardize_molblock(molecule.o_molblock)

        # Standardize and get parent molecule molblock
        #parent_molblock, _ = standardizer.get_parent_molblock(molecule.o_molblock)
        std_mol = dm.read_molblock(molecule.std_molblock)

        # Compute molecular representations
        molecule.smiles_canonical = dm.to_smiles(std_mol)
        molecule.selfies = dm.to_selfies(std_mol)
        molecule.inchi = dm.to_inchi(std_mol)
        molecule.inchi_key = dm.to_inchikey(std_mol)
        molecule.smarts = dm.to_smarts(std_mol)

        # Compute descriptors and update molecule
        descriptors = dm.descriptors.compute_many_descriptors(std_mol)
        molecule = molecule.model_copy(update=descriptors)

        # Check RO5 compliance
        molecule.ro5_compliant = Ro5(molecule)

        logger.info(f"Standardized molecule: {molecule.model_dump()}")
        return molecule

    except ValueError as ve:
        logger.error(f"Invalid molecule data: {ve}")
        raise ve

    except Exception as e:
        logger.error(f"Error processing molecule: {e}")
        raise Exception("Internal error")
