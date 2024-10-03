from typing import List
import datamol as dm
from pydantic import UUID4
from app.schemas.cluster_dto import ClusterInputDto, ClusterOutputDto
from app.core.logging_config import logger

def cluster_molecules_with_centroids(
    molecule_list: List[ClusterInputDto], cutoff=0.7
) -> List[ClusterOutputDto]:
    """
    Cluster molecules based on structural similarity and mark centroid molecules in the result.

    Args:
        molecule_list (List[ClusterInputDto]): A list of ClusterInputDto objects, each containing 'id' (UUID4), 
                                               'name' (optional), and 'smiles' (SMILES representation of the molecule).
        cutoff (float): The similarity cutoff for clustering (default is 0.7).

    Returns:
        List[ClusterOutputDto]: A list of ClusterOutputDto objects with 'id' (UUID4), 'name', 'smiles', 'cluster', and 'centroid'.
    """

    # Validate cutoff value
    if not (0 < cutoff <= 1):
        raise ValueError("Invalid cutoff: Cutoff must be a float between 0 and 1.")

    # Initialize lists to store canonical SMILES and RDKit Mol objects
    canonical_smiles_list = []
    mols = []

    # Convert SMILES to canonical SMILES and RDKit Mol objects
    for mol_data in molecule_list:
        try:
            mol = dm.to_mol(mol_data.smiles)
            if mol is None:
                raise ValueError(f"Could not parse SMILES: {mol_data.smiles}")
            canonical_smiles = dm.to_smiles(mol, canonical=True)
            canonical_smiles_list.append({
                "id": mol_data.id,  # Keep UUID4 as is
                "name": mol_data.name,  # Include name if it exists
                "smiles": canonical_smiles,
            })
            mols.append(mol)
        except Exception as e:
            raise ValueError(f"Error processing molecule with ID {mol_data.id}: {e}")

    # Cluster the molecules based on similarity
    try:
        clusters, mol_clusters = dm.cluster_mols(mols, cutoff=cutoff)
    except Exception as e:
        raise RuntimeError(f"Error during clustering: {e}")

    # Determine the number of clusters
    num_clusters = len(mol_clusters)

    # Select the centroid molecule for each cluster
    try:
        indices, centroids = dm.pick_centroids(mols, npick=num_clusters, threshold=cutoff, method="sphere", n_jobs=-1)
    except Exception as e:
        raise RuntimeError(f"Error selecting centroids: {e}")

    # Map molecules to their clusters and mark centroid molecules
    molecule_clusters = []
    centroid_indices_set = set(indices)  # Convert centroid indices to a set for quick lookup

    for i, mol_cluster in enumerate(mol_clusters):
        for mol in mol_cluster:
            mol_smiles = dm.to_smiles(mol, canonical=True)
            mol_data = next((m for m in canonical_smiles_list if m["smiles"] == mol_smiles), None)
            if mol_data is not None:
                # Check if the molecule is a centroid
                is_centroid = canonical_smiles_list.index(mol_data) in centroid_indices_set
                # Create ClusterOutputDto entry
                molecule_clusters.append(ClusterOutputDto(
                    id=mol_data["id"],
                    name=mol_data["name"],
                    smiles=mol_data["smiles"],
                    cluster=i + 1,  # Cluster number starts from 1 for readability
                    centroid=is_centroid
                ))
            else:
                raise RuntimeError(f"Failed to find molecule data for SMILES: {mol_smiles}")

    return molecule_clusters
