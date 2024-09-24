from sqlalchemy import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.molecule import Molecule
from app.schemas.molecule import MoleculeBase, MoleculeCreate, MoleculeUpdate
from app.core.logging_config import logger
from fastapi import HTTPException
from app.schemas.similar_molecule_dto import SimilarMoleculeDto
from app.utils.molecules import fp_gen
from app.utils.molecules.helper import standardize_smiles
import datamol as dm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text
from typing import List, Dict, Any


# Fetch a molecule by its ID from the database
async def get_molecule(db: AsyncSession, id: UUID):
    try:
        logger.info(f"Fetching molecule with ID: {id}")
        result = await db.execute(select(Molecule).filter(Molecule.id == id))
        db_molecule = result.scalar()
        if not db_molecule:
            logger.info(f"Molecule with ID {id} not found")
            return None
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except Exception as e:
        logger.error(f"Error fetching molecule with ID {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def get_molecule_by_smiles(db: AsyncSession, smiles_canonical: str):
    try:
        logger.debug(f"Fetching molecule with SMILES : {smiles_canonical}")
        # standardize the smiles
        std_smiles_canonical = standardize_smiles(smiles_canonical)
        result = await db.execute(
            select(Molecule).filter(Molecule.smiles_canonical == std_smiles_canonical)
        )
        db_molecule = result.scalar()
        if not db_molecule:
            logger.debug(f"Molecule with SMILES {smiles_canonical} not found")
            return None
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except ValueError as ve:
        logger.error(f"Invalid molecule smiles_canonical : {smiles_canonical}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule smiles: {ve}")
    except Exception as e:
        logger.error(f"Error fetching molecule with SMILES {smiles_canonical}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Create a new molecule and commit it to the database
async def create_molecule(db: AsyncSession, molecule: MoleculeCreate):
    try:
        logger.debug(f"Creating a new molecule with data: {molecule.model_dump()}")
        db_molecule = Molecule(**molecule.model_dump())

        # Mol
        db_molecule.mol = db_molecule.smiles_canonical
        # Fingerprints
        db_molecule.morgan_fp = fp_gen.generate_morgan_fp(db_molecule.mol)
        db_molecule.rdkit_fp = fp_gen.generate_rdkit_fp(db_molecule.mol)

        logger.debug(f"Inserting molecule: {db_molecule}")

        db.add(db_molecule)
        await db.commit()
        await db.refresh(db_molecule)
        logger.debug(f"Molecule created successfully: {db_molecule}")
        return db_molecule

    except IntegrityError as e:
        logger.error(f"Duplicate primary key error: {molecule.id} {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(
            status_code=400, detail="Molecule with this ID already exists."
        )

    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        await db.rollback()  # Rollback transaction on error
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Update an existing molecule by its ID
async def update_molecule(db: AsyncSession, id: UUID, molecule: MoleculeUpdate):
    try:
        logger.info(f"Updating molecule with ID: {id}")
        db_molecule = await get_molecule(db, id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        update_data = molecule.model_dump()
        for key, value in update_data.items():
            if hasattr(db_molecule, key) and value is not None:
                setattr(db_molecule, key, value)

        db.add(db_molecule)
        await db.commit()
        await db.refresh(db_molecule)
        logger.debug(f"Molecule updated successfully: {db_molecule}")
        return db_molecule
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error updating molecule with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Delete a molecule by its ID
async def delete_molecule(db: AsyncSession, id: UUID):
    try:
        logger.info(f"Deleting molecule with ID: {id}")
        db_molecule = await get_molecule(db, id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        await db.delete(db_molecule)
        await db.commit()
        logger.info(f"Molecule with ID {id} deleted successfully")
    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error deleting molecule with ID {id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Similarity search
async def search_similar_molecules(
    db: AsyncSession, query_smiles: str, threshold: float = 0.7, limit: int = 100
) -> List[SimilarMoleculeDto]:
    """
    Searches for molecules with a Tanimoto similarity score above the given threshold.

    Args:
        db (AsyncSession): Database session to execute the query.
        query_fp (str): The binary string representing the query molecule's fingerprint.
        threshold (float, optional): The similarity score threshold. Defaults to 0.7.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the molecule details and similarity score.
    """
    try:
        # Convert SMILES to fingerprint
        query_fp = fp_gen.generate_morgan_fp(query_smiles)
        # Define parameterized query to prevent SQL injection
        query = text(
            """
            SELECT *, 
                   tanimoto_sml(morgan_fp, :query_fp) AS similarity
            FROM molecules
            WHERE tanimoto_sml(morgan_fp, :query_fp) >= :threshold
            ORDER BY similarity DESC
            LIMIT :limit;
        """
        )

        # Execute the query with parameters
        result = await db.execute(
            query, {"query_fp": query_fp, "threshold": threshold, "limit": limit}
        )

        # Fetch all results and return as a list of dictionaries
        molecules = result.mappings().all()

        logger.info(f"Found {len(molecules)} molecules with similarity > {threshold}")
        return molecules

    except Exception as e:
        logger.error(f"Error executing similarity search: {e}")
        raise


# Substructure search
async def search_substructure_molecules(
    db: AsyncSession, query_smiles: str, limit: int = 100
) -> List[MoleculeBase]:
    """
    Searches for molecules containing the query molecule as a substructure.

    Args:
        db (AsyncSession): Database session to execute the query.
        query_fp (str): The binary string representing the query molecule's fingerprint.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the molecule details.
    """
    try:

        # Define parameterized query to prevent SQL injection
        # query = text(
        #     """
        #     SELECT id, name, mol
        #     FROM molecules
        #     WHERE mol @@ :query_mol;
        # """
        # )
        query = text(
            """
            SELECT *
            FROM molecules
            WHERE mol @> :query_smiles
            LIMIT :limit;
        """
        )

        # Execute the query with parameters
        result = await db.execute(query, {"query_smiles": query_smiles, "limit": limit})

        # Fetch all results and return as a list of dictionaries
        molecules = result.mappings().all()

        logger.info(f"Found {len(molecules)} molecules containing the substructure")
        return molecules

    except Exception as e:
        logger.error(f"Error executing substructure search: {e}")
        raise


async def search_substructure_multiple(
    db: AsyncSession, smiles_list: List[str], condition: str = "OR", limit: int = 100
) -> List[MoleculeBase]:
    """
    Performs a substructure search to find molecules containing any of the provided substructures.

    Args:
        db (AsyncSession): The database session to execute queries.
        query_mols (List[str]): A list of MolBlock representations of the query substructures.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the molecules that match any substructure.

    Raises:
        HTTPException: If an error occurs during the substructure search.
    """
    try:
        logger.info(
            f"Starting substructure search with {len(smiles_list)} substructures..."
        )

        # Dynamically construct the WHERE clause based on the condition
        condition = condition.upper()
        # Check if the condition is valid
        if condition not in ["OR", "AND"]:
            raise ValueError("Invalid condition. Must be 'OR' or 'AND'.")

        # Construct the conditions based on the condition
        conditions = " OR ".join(
            [f"mol @> :smiles_{i}" for i in range(len(smiles_list))]
        )
        if condition == "AND":
            conditions = " AND ".join(
                [f"mol @> :smiles_{i}" for i in range(len(smiles_list))]
            )

        # Define the query using dynamic conditions
        query = text(
            f"""
            SELECT *
            FROM molecules
            WHERE {conditions}
            LIMIT :limit;
        """
        )

        # Prepare the parameters with query mols
        params = {f"smiles_{i}": smiles for i, smiles in enumerate(smiles_list)}
        params["limit"] = limit

        # Execute the query with the substructures
        result = await db.execute(query, params)

        # Fetch all results
        molecules = result.mappings().all()

        logger.info(f"Found {len(molecules)} molecules matching the substructures")
        return molecules

    except Exception as e:
        logger.error(f"Error performing substructure search: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while performing the substructure search",
        )




async def bulk_create_molecules(new_molecules, db: AsyncSession):
    """
    Bulk create new molecules in the database.

    :param new_molecules: List of molecules to be created.
    :param db: AsyncSession to interact with the database.
    """
    try:
        db.add_all(new_molecules)
        await db.commit()
        logger.info(f"Successfully created {len(new_molecules)} molecules.")
    except Exception as e:
        logger.error(f"Error during bulk molecule creation: {e}")
        await db.rollback()
        raise e