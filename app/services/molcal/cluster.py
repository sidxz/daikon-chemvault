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

    # Initialize mappings
    canonical_smiles_dict = {}
    mols = []
    id_order = []
    
    logger.info(f"Starting clustering with {len(molecule_list)} molecules with cutoff {cutoff}.")

    # Convert SMILES to canonical SMILES and RDKit Mol objects
    for mol_data in molecule_list:
        try:
            mol = dm.to_mol(mol_data.smiles)
            if mol is None:
                raise ValueError(f"Could not parse SMILES: {mol_data.smiles}")
            canonical_smiles = dm.to_smiles(mol, canonical=True)
            canonical_smiles_dict[mol_data.id] = {
                "id": mol_data.id,
                "name": mol_data.name,
                "smiles": canonical_smiles,
            }
            mols.append(mol)
            id_order.append(mol_data.id)
        except Exception as e:
            raise ValueError(f"Error processing molecule with ID {mol_data.id}: {e}")

    # Cluster the molecules based on similarity
    try:
        clusters, mol_clusters = dm.cluster_mols(mols, cutoff=cutoff)
    except Exception as e:
        raise RuntimeError(f"Error during clustering: {e}")

    # Determine number of clusters
    num_clusters = len(mol_clusters)

    # Select centroid molecules for each cluster
    try:
        indices, centroids = dm.pick_centroids(mols, npick=num_clusters, threshold=cutoff, method="sphere", n_jobs=-1)
    except Exception as e:
        raise RuntimeError(f"Error selecting centroids: {e}")

    # Map molecules to their clusters and mark centroid molecules
    molecule_clusters = []
    centroid_indices_set = set(indices)

    for i, mol_cluster in enumerate(mol_clusters):
        for mol in mol_cluster:
            # Use index position to map back to original molecule ID
            mol_index = mols.index(mol)
            mol_id = id_order[mol_index]
            mol_data = canonical_smiles_dict[mol_id]

            is_centroid = mol_index in centroid_indices_set

            # Append the ClusterOutputDto entry
            molecule_clusters.append(ClusterOutputDto(
                id=mol_data["id"],
                name=mol_data["name"],
                smiles=mol_data["smiles"],
                cluster=i + 1,  # Cluster index starts from 1
                centroid=is_centroid
            ))

    return molecule_clusters
