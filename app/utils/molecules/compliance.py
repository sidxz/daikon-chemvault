from app.schemas.molecule import MoleculeBase

def Ro5(molecule: MoleculeBase) -> bool:
    """Check if a molecule is Rule of 5 compliant."""
    # Safely retrieve values, default to None
    mw = molecule.mw if molecule.mw is not None else float('inf')
    clogp = molecule.clogp if molecule.clogp is not None else float('inf')
    n_lipinski_hbd = molecule.n_lipinski_hbd if molecule.n_lipinski_hbd is not None else float('inf')
    n_lipinski_hba = molecule.n_lipinski_hba if molecule.n_lipinski_hba is not None else float('inf')

    # Check if the molecule is Rule of 5 compliant
    if mw > 500 or clogp > 5 or n_lipinski_hbd > 5 or n_lipinski_hba > 10:
        return False
    return True
