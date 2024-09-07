import datamol as dm
from chembl_structure_pipeline import standardizer


def standardize_smiles(smiles: str) -> str:
    """Standardize a SMILES string.

    Args:
        smiles (str): The SMILES string to be standardized.

    Returns:
        str: The standardized canonical SMILES string.

    Raises:
        ValueError: If the SMILES cannot be converted to a molecule.
    """
    # Convert SMILES to a molecule
    molecule = dm.to_mol(smiles)
    if molecule is None:
        raise ValueError(f"Unable to convert SMILES to molecule: {smiles}")

    # Standardize the molecule and get the standard molblock
    standardized_molblock = standardizer.standardize_molblock(dm.to_molblock(molecule))

    # Read the standardized molblock back to a molecule
    standardized_molecule = dm.read_molblock(standardized_molblock)

    # Convert the standardized molecule back to canonical SMILES
    standardized_smiles_canonical = dm.to_smiles(standardized_molecule)

    return standardized_smiles_canonical
