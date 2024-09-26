from app.repositories.molecule import search_similar_molecules
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.core.logging_config import logger
from typing import List, Dict, Any

from app.schemas.similar_molecule_dto import SimilarMoleculeDto
from app.utils.molecules import fp_gen
from app.utils.molecules.helper import standardize_smiles


async def find_similar_molecules(
    db: AsyncSession,
    query_molecule: str,
    threshold: float = 0.7,
    limit: int = 100,
    filters: Dict[str, Any] = None,
) -> List[SimilarMoleculeDto]:
    """
    Fetches molecules from the database with a similarity score above the threshold.

    Args:
        db (AsyncSession): The database session to execute queries.
        query_fp (str): The fingerprint of the query molecule.
        threshold (float, optional): The similarity threshold. Defaults to 0.7.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the similar molecules.

    Raises:
        HTTPException: If an error occurs during the similarity search.
    """
    try:
        logger.info(f"Initiating similarity search with threshold: {threshold}")
        standard_query_smiles = standardize_smiles(query_molecule)

        # Call the repository function to execute the similarity search
        results = await search_similar_molecules(
            db=db,
            query_smiles=standard_query_smiles,
            threshold=threshold,
            limit=limit,
            filters=filters,
        )

        if not results:
            logger.warning(f"No molecules found with similarity above {threshold}")
        else:
            logger.info(f"Similarity search completed with {len(results)} results")

        return results

    except Exception as e:
        logger.error(f"Error performing similarity search: {e}")
        # Raise a detailed HTTP exception with a 500 status code
        raise HTTPException(
            status_code=500,
            detail="An error occurred while performing the similarity search",
        )
