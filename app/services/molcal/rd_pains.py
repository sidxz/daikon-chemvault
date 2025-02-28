from pydantic import UUID4, BaseModel
from typing import List, Optional
import uuid
from rdkit import Chem
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

from app.schemas.pains_dto import PainsInputDto, PainsOutputDto


def load_pains_filters() -> FilterCatalog:
    """
    Load the PAINS filter catalog from RDKit.

    Returns:
        FilterCatalog: An RDKit filter catalog containing PAINS filters.
    """
    catalog_params = FilterCatalogParams()
    catalog_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    catalog_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
    return FilterCatalog(catalog_params)


def check_pains(mol: Chem.Mol, catalog: FilterCatalog) -> List[str]:
    """
    Check if a molecule matches any PAINS filters.

    Args:
        mol (Chem.Mol): RDKit molecule object.
        catalog (FilterCatalog): RDKit PAINS filter catalog.

    Returns:
        List[str]: List of matching PAINS rule descriptions. Empty list if no matches found.
    """
    return sorted(set(entry.GetDescription() for entry in catalog.GetMatches(mol)))


def detect_pains(molecule_list: List[PainsInputDto]) -> List[PainsOutputDto]:
    """
    Detect PAINS patterns in a list of molecules.

    Args:
        molecule_list (List[PainsInputDto]): List of molecules with ID, name, and SMILES representation.

    Returns:
        List[PainsOutputDto]: List of molecules with PAINS classification.
    """
    pains_results = []
    catalog = load_pains_filters()

    for mol_data in molecule_list:
        try:

            # Convert SMILES to RDKit Mol object
            mol = Chem.MolFromSmiles(mol_data.smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {mol_data.smiles}")

            # Check for PAINS matches
            pains_matches = check_pains(mol, catalog)
            has_pains = bool(pains_matches)

            # Append results
            pains_results.append(
                PainsOutputDto(
                    id=mol_data.id,
                    name=mol_data.name,
                    smiles=mol_data.smiles,
                    rdkit_pains=has_pains,
                    rdkit_pains_label=pains_matches if has_pains else None,
                )
            )
        except Exception as e:
            raise RuntimeError(
                f"Error processing molecule '{mol_data.name or 'Unknown'}' with SMILES {mol_data.smiles}: {e}"
            )

    return pains_results
