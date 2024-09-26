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
from sqlalchemy.sql import text, or_
from typing import List, Dict, Any, Tuple


def generate_filter_conditions(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Generates SQL filter conditions and corresponding parameters based on the filters.

    Args:
        filters (Dict[str, Any]): A dictionary containing the filter conditions.

    Returns:
        Tuple[str, Dict[str, Any]]: A tuple containing the SQL condition string and the parameters.
    """
    filter_conditions = []
    filter_params = {}

    if filters:
        if "molecular_weight_min" in filters:
            filter_conditions.append("mw >= :molecular_weight_min")
            filter_params["molecular_weight_min"] = filters["molecular_weight_min"]

        if "molecular_weight_max" in filters:
            filter_conditions.append("mw <= :molecular_weight_max")
            filter_params["molecular_weight_max"] = filters["molecular_weight_max"]

        if "clogp_min" in filters:
            filter_conditions.append("clogp >= :clogp_min")
            filter_params["clogp_min"] = filters["clogp_min"]

        if "clogp_max" in filters:
            filter_conditions.append("clogp <= :clogp_max")
            filter_params["clogp_max"] = filters["clogp_max"]

        if "lipinski_hbd_min" in filters:
            filter_conditions.append("n_lipinski_hbd >= :lipinski_hbd_min")
            filter_params["lipinski_hbd_min"] = filters["lipinski_hbd_min"]

        if "lipinski_hbd_max" in filters:
            filter_conditions.append("n_lipinski_hbd <= :lipinski_hbd_max")
            filter_params["lipinski_hbd_max"] = filters["lipinski_hbd_max"]

        if "lipinski_hba_min" in filters:
            filter_conditions.append("n_lipinski_hba >= :lipinski_hba_min")
            filter_params["lipinski_hba_min"] = filters["lipinski_hba_min"]

        if "lipinski_hba_max" in filters:
            filter_conditions.append("n_lipinski_hba <= :lipinski_hba_max")
            filter_params["lipinski_hba_max"] = filters["lipinski_hba_max"]

        if "tpsa_min" in filters:
            filter_conditions.append("tpsa >= :tpsa_min")
            filter_params["tpsa_min"] = filters["tpsa_min"]

        if "tpsa_max" in filters:
            filter_conditions.append("tpsa <= :tpsa_max")
            filter_params["tpsa_max"] = filters["tpsa_max"]

        if "rotatable_bonds_min" in filters:
            filter_conditions.append("n_rotatable_bonds >= :rotatable_bonds_min")
            filter_params["rotatable_bonds_min"] = filters["rotatable_bonds_min"]

        if "rotatable_bonds_max" in filters:
            filter_conditions.append("n_rotatable_bonds <= :rotatable_bonds_max")
            filter_params["rotatable_bonds_max"] = filters["rotatable_bonds_max"]

        if "heavy_atoms_min" in filters:
            filter_conditions.append("n_heavy_atoms >= :heavy_atoms_min")
            filter_params["heavy_atoms_min"] = filters["heavy_atoms_min"]

        if "heavy_atoms_max" in filters:
            filter_conditions.append("n_heavy_atoms <= :heavy_atoms_max")
            filter_params["heavy_atoms_max"] = filters["heavy_atoms_max"]

        if "aromatic_rings_min" in filters:
            filter_conditions.append("n_aromatic_rings >= :aromatic_rings_min")
            filter_params["aromatic_rings_min"] = filters["aromatic_rings_min"]

        if "aromatic_rings_max" in filters:
            filter_conditions.append("n_aromatic_rings <= :aromatic_rings_max")
            filter_params["aromatic_rings_max"] = filters["aromatic_rings_max"]

        if "rings_min" in filters:
            filter_conditions.append("n_rings >= :rings_min")
            filter_params["rings_min"] = filters["rings_min"]

        if "rings_max" in filters:
            filter_conditions.append("n_rings <= :rings_max")
            filter_params["rings_max"] = filters["rings_max"]

    # Return the generated SQL condition string and the corresponding parameters
    return " AND ".join(filter_conditions), filter_params


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


# Fetch molecule by name, return similar names and if name is found in synonyms


async def get_molecule_by_name(db: AsyncSession, name: str, limit: int = 100):
    try:
        logger.info(
            f"Fetching molecules with name or matching in synonyms: {name} (limit: {limit})"
        )

        # Query to find molecules with matching name or in synonyms with limit
        result = await db.execute(
            select(Molecule)
            .filter(
                or_(
                    Molecule.name.ilike(
                        f"%{name}%"
                    ),  # Case-insensitive partial match for name
                    Molecule.synonyms.ilike(
                        f"%{name}%"
                    ),  # Check in synonyms field (case-insensitive)
                )
            )
            .limit(limit)
        )

        # Fetch all matching molecules up to the limit
        db_molecules = result.scalars().all()

        if not db_molecules:
            logger.info(f"No molecules found for {name}")
            return {"message": f"No molecules found for {name}"}

        logger.debug(f"Molecules fetched successfully: {db_molecules}")

        # Return the list of molecules
        return db_molecules

    except Exception as e:
        logger.error(f"Error fetching molecules with name {name}: {e}")
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

        # Fetch the molecule by its ID
        db_molecule = await get_molecule(db, id)
        if not db_molecule:
            raise HTTPException(status_code=404, detail="Molecule not found")

        # Update only the fields provided (non-None)
        update_data = molecule.model_dump(exclude_unset=True)  # Exclude unset fields
        if update_data:
            for key, value in update_data.items():
                setattr(db_molecule, key, value)
            # Commit the updated molecule
            await db.commit()
            await db.refresh(db_molecule)  # Refresh the instance with the latest data
            logger.debug(f"Molecule updated successfully: {db_molecule}")
        else:
            logger.info("No fields to update.")

        return db_molecule

    except HTTPException as e:
        raise e  # Re-raise HTTPException without modification
    except Exception as e:
        logger.error(f"Error updating molecule with ID {id}: {e}")
        await db.rollback()  # Rollback in case of error
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
    db: AsyncSession,
    query_smiles: str,
    threshold: float = 0.9,
    limit: int = 100,
    filters: Dict[str, Any] = None,
) -> List[SimilarMoleculeDto]:
    """
    Searches for molecules with a Tanimoto similarity score above the given threshold.

    Args:
        db (AsyncSession): Database session to execute the query.
        query_smiles (str): The SMILES string of the query molecule.
        threshold (float, optional): The similarity score threshold. Defaults to 0.9.
        limit (int, optional): Maximum number of results to return. Defaults to 100.
        filters (Dict[str, Any], optional): Optional filters for molecular properties.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the molecule details and similarity score.
    """
    try:
        # Convert SMILES to fingerprint
        query_fp = fp_gen.generate_morgan_fp(query_smiles)

        # Base SQL query
        sql_query = """
            SELECT *, 
                   tanimoto_sml(morgan_fp, :query_fp) AS similarity
            FROM molecules
            WHERE tanimoto_sml(morgan_fp, :query_fp) >= :threshold
        """

        # Generate filter conditions and parameters
        filter_conditions, filter_params = generate_filter_conditions(filters)

        # If there are any filter conditions, append them to the base query
        if filter_conditions:
            sql_query += " AND " + filter_conditions

        # Append the ORDER BY and LIMIT clauses
        sql_query += """
            ORDER BY similarity DESC
            LIMIT :limit;
        """

        # Create the SQLAlchemy text object
        query = text(sql_query)

        # Define the parameters, including the dynamic filters
        parameters = {
            "query_fp": query_fp,
            "threshold": threshold,
            "limit": limit,
        }
        parameters.update(filter_params)

        # Execute the query with parameters
        result = await db.execute(query, parameters)

        # Fetch all results and return as a list of dictionaries
        molecules = result.mappings().all()

        logger.info(f"Found {len(molecules)} molecules with similarity > {threshold}")
        return molecules

    except Exception as e:
        logger.error(f"Error executing similarity search: {e}")
        raise


# Substructure search
async def search_substructure_molecules(
    db: AsyncSession,
    query_smiles: str,
    limit: int = 100,
    filters: Dict[str, Any] = None,
) -> List[MoleculeBase]:
    """
    Searches for molecules containing the query molecule as a substructure with optional filters.

    Args:
        db (AsyncSession): Database session to execute the query.
        query_smiles (str): The SMILES string of the query molecule.
        limit (int, optional): Maximum number of results to return. Defaults to 100.
        filters (Dict[str, Any], optional): Optional filters for molecular properties.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the molecule details.
    """
    try:
        # Base SQL query
        sql_query = """
            SELECT *
            FROM molecules
            WHERE mol @> :query_smiles
        """

        # Generate filter conditions and parameters
        filter_conditions, filter_params = generate_filter_conditions(filters)

        # If there are any filter conditions, append them to the base query
        if filter_conditions:
            sql_query += " AND " + filter_conditions

        # Append the LIMIT clause
        sql_query += """
            LIMIT :limit;
        """

        # Create the SQLAlchemy text object
        query = text(sql_query)

        # Define the parameters, including the dynamic filters
        parameters = {
            "query_smiles": query_smiles,
            "limit": limit,
        }
        parameters.update(filter_params)

        # Execute the query with parameters
        result = await db.execute(query, parameters)

        # Fetch all results and return as a list of dictionaries
        molecules = result.mappings().all()

        logger.info(f"Found {len(molecules)} molecules containing the substructure")
        return molecules

    except Exception as e:
        logger.error(f"Error executing substructure search: {e}")
        raise


async def search_substructure_multiple(
    db: AsyncSession,
    smiles_list: List[str],
    condition: str = "OR",
    limit: int = 100,
    filters: Dict[str, Any] = None,
) -> List[MoleculeBase]:
    """
    Performs a substructure search to find molecules containing any of the provided substructures with optional filters.

    Args:
        db (AsyncSession): The database session to execute queries.
        smiles_list (List[str]): A list of SMILES representations of the query substructures.
        condition (str, optional): The logical condition to combine the substructure matches ('OR' or 'AND'). Defaults to "OR".
        limit (int, optional): Maximum number of results to return. Defaults to 100.
        filters (Dict[str, Any], optional): Optional filters for molecular properties.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the molecules that match the substructures.
    """
    try:
        logger.info(
            f"Starting substructure search with {len(smiles_list)} substructures..."
        )

        # Ensure condition is valid
        condition = condition.upper()
        if condition not in ["OR", "AND"]:
            raise ValueError("Invalid condition. Must be 'OR' or 'AND'.")

        # Construct the substructure conditions dynamically
        substructure_conditions = f" {condition} ".join(
            [f"mol @> :smiles_{i}" for i in range(len(smiles_list))]
        )

        # Base SQL query with substructure conditions
        sql_query = f"""
            SELECT *
            FROM molecules
            WHERE {substructure_conditions}
        """

        # Generate filter conditions and parameters using the helper function
        filter_conditions, filter_params = generate_filter_conditions(filters)

        # Append the filter conditions if any are present
        if filter_conditions:
            sql_query += " AND " + filter_conditions

        # Append the LIMIT clause
        sql_query += """
            LIMIT :limit;
        """

        # Create the SQLAlchemy text object
        query = text(sql_query)

        # Prepare the parameters for the SMILES list
        params = {f"smiles_{i}": smiles for i, smiles in enumerate(smiles_list)}
        params["limit"] = limit

        # Add filter values to the parameters dictionary
        params.update(filter_params)

        # Execute the query with the substructures and filters
        result = await db.execute(query, params)

        # Fetch all results and return as a list of dictionaries
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
