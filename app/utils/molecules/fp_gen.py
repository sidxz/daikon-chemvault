from typing import Union
from app.db.models.molecule import MolType
import datamol as dm
from app.core.logging_config import logger

def generate_morgan_fp(mol: Union[str, MolType], radius: int = 3) -> str:
    """Generate Morgan fingerprints for a molecule.
    
    Args:
        mol (MolType): The molecule object to generate the fingerprint for.
        radius (int): The radius of the Morgan fingerprint. Default is 3.
    
    Returns:
        str: The Morgan fingerprint as a bitstring.
    
    Raises:
        ValueError: If there is an issue generating the fingerprint.
    """
    if mol is None:
        raise ValueError("Molecule cannot be None.")
    
    try:
        logger.debug(f"Generating Morgan fingerprint with radius={radius}")
        # Generate Morgan fingerprint with datamol
        morgan_fp = dm.to_fp(mol, as_array=False, radius=radius, includeChirality=True)
        return morgan_fp.ToBitString()
    except Exception as e:
        logger.error(f"Error generating Morgan fingerprint: {e}")
        raise ValueError(f"Error generating Morgan fingerprint: {e}")


def generate_rdkit_fp(mol: Union[str, MolType]) -> str:
    """Generate RDKit fingerprints for a molecule.
    
    Args:
        mol (MolType): The molecule object to generate the fingerprint for.
    
    Returns:
        str: The RDKit fingerprint as a bitstring.
    
    Raises:
        ValueError: If there is an issue generating the fingerprint.
    """
    if mol is None:
        raise ValueError("Molecule cannot be None.")
    
    try:
        logger.debug("Generating RDKit fingerprint")
        # Generate RDKit fingerprint with datamol
        rdkit_fp = dm.to_fp(mol, as_array=False, fp_type="rdkit")
        return rdkit_fp.ToBitString()
    except Exception as e:
        logger.error(f"Error generating RDKit fingerprint: {e}")
        raise ValueError(f"Error generating RDKit fingerprint: {e}")
