from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import SessionLocal
from app.repositories import molecule as molecule_repo
from app.schemas.molecule_dto import InputMoleculeDto
from app.core.logging_config import logger
from app.schemas.similar_molecule_dto import SimilarMoleculeDto
from app.services.molecule import batch_registration, registration
from app.schemas.molecule import MoleculeBase
from app.repositories.molecule import (
    get_molecule,
    get_molecule_by_name,
    get_molecule_by_smiles,
    search_substructure_multiple,
)
from app.services.molecule.batch_registration_parent import process_all_molecule_batches
from app.services.molecule.similarity import find_similar_molecules

router = APIRouter()


# Dependency to get the database session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@router.post("/", response_model=MoleculeBase)
async def create_molecule(
    molecule: InputMoleculeDto, db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"Creating a new molecule with data: {molecule.model_dump()}")
        # result = await molecule_repo.create_molecule(db=db, molecule=molecule)
        result = await registration.register(molecule, db)
        logger.debug(f"Molecule created successfully: {result}")
        return result

    except ValueError as ve:
        logger.error(f"Invalid molecule data: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule data: {ve}")
    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/by-id/{id}", response_model=MoleculeBase)
async def read_molecule(id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Fetching molecule with ID: {id}")
        db_molecule = await get_molecule(db=db, id=id)
        if db_molecule is None:
            logger.warning(f"Molecule with ID {id} not found")
            raise HTTPException(status_code=404, detail=f"Molecule not found, ID: {id}")
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except HTTPException as e:
        raise e
    except ValueError as ve:
        logger.error(f"Invalid molecule id : {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule id: {ve}")
    except Exception as e:
        logger.error(f"Error fetching molecule with ID {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/by-name", response_model=List[MoleculeBase])
async def read_molecule_by_name(
    name: str, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"Fetching molecule with Name: {name}")
        db_molecule = await get_molecule_by_name(db=db, name=name, limit=limit)
        if db_molecule is None:
            logger.warning(f"Molecule with name {name} not found")
            raise HTTPException(status_code=404, detail=f"Molecule not found, ID: {name}")
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except HTTPException as e:
        raise e
    except ValueError as ve:
        logger.error(f"Invalid molecule name : {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule name: {ve}")
    except Exception as e:
        logger.error(f"Error fetching molecule with name {name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/by-smiles-canonical", response_model=MoleculeBase)
async def read_molecule(smiles: str, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Fetching molecule with canonical smiles: {smiles}")
        db_molecule = await get_molecule_by_smiles(db=db, smiles_canonical=smiles)
        if db_molecule is None:
            logger.warning(f"Molecule with smiles_canonical {smiles} not found")
            raise HTTPException(
                status_code=404, detail=f"Molecule not found CANONICAL SMILES: {smiles}"
            )
        logger.debug(f"Molecule fetched successfully: {db_molecule}")
        return db_molecule
    except ValueError as ve:
        logger.error(f"Invalid molecule smiles_canonical : {smiles}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule id: {ve}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching molecule with smiles_canonical {smiles}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.put("/{molecule_id}", response_model=schemas.Molecule)
# async def update_molecule(
#     molecule_id: int,
#     molecule: schemas.MoleculeUpdate,
#     db: AsyncSession = Depends(get_db),
# ):
#     try:
#         logger.info(
#             f"Updating molecule with ID: {molecule_id} with data: {molecule.model_dump()}"
#         )
#         result = await molecule_repo.update_molecule(
#             db=db, molecule_id=molecule_id, molecule=molecule
#         )
#         logger.debug(f"Molecule updated successfully: {result}")
#         return result
#     except HTTPException as e:
#         raise e  # Re-raise HTTPException without modification
#     except Exception as e:
#         logger.error(f"Error updating molecule with ID {molecule_id}: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.delete("/{molecule_id}")
# async def delete_molecule(molecule_id: int, db: AsyncSession = Depends(get_db)):
#     try:
#         logger.info(f"Deleting molecule with ID: {molecule_id}")
#         await molecule_repo.delete_molecule(db=db, molecule_id=molecule_id)
#         logger.debug(f"Molecule with ID {molecule_id} deleted successfully")
#         return {"detail": "Molecule deleted"}
#     except HTTPException as e:
#         raise e  # Re-raise HTTPException without modification
#     except Exception as e:
#         logger.error(f"Error deleting molecule with ID {molecule_id}: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/similarity", response_model=List[SimilarMoleculeDto])
async def similarity_search(
    smiles: str,
    threshold: float = 0.7,
    limit: int = 100,
    molecular_weight_min: Optional[float] = None,
    molecular_weight_max: Optional[float] = None,
    clogp_min: Optional[float] = None,
    clogp_max: Optional[float] = None,
    lipinski_hbd_min: Optional[int] = None,
    lipinski_hbd_max: Optional[int] = None,
    tpsa_min: Optional[float] = None,
    tpsa_max: Optional[float] = None,
    rotatable_bonds_min: Optional[int] = None,
    rotatable_bonds_max: Optional[int] = None,
    heavy_atoms_min: Optional[int] = None,
    heavy_atoms_max: Optional[int] = None,
    aromatic_rings_min: Optional[int] = None,
    aromatic_rings_max: Optional[int] = None,
    rings_min: Optional[int] = None,
    rings_max: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    # Prepare a dictionary of filters with non-None values
    filters = {
        "molecular_weight_min": molecular_weight_min,
        "molecular_weight_max": molecular_weight_max,
        "clogp_min": clogp_min,
        "clogp_max": clogp_max,
        "lipinski_hbd_min": lipinski_hbd_min,
        "lipinski_hbd_max": lipinski_hbd_max,
        "tpsa_min": tpsa_min,
        "tpsa_max": tpsa_max,
        "rotatable_bonds_min": rotatable_bonds_min,
        "rotatable_bonds_max": rotatable_bonds_max,
        "heavy_atoms_min": heavy_atoms_min,
        "heavy_atoms_max": heavy_atoms_max,
        "aromatic_rings_min": aromatic_rings_min,
        "aromatic_rings_max": aromatic_rings_max,
        "rings_min": rings_min,
        "rings_max": rings_max,
    }

    # Clean the dictionary by removing filters that are None
    filters = {k: v for k, v in filters.items() if v is not None}

    # Pass the filters dictionary to the molecule search function
    results = await find_similar_molecules(
        db=db, query_molecule=smiles, threshold=threshold, limit=limit, filters=filters
    )

    return results


@router.get("/substructure", response_model=List[MoleculeBase])
async def substructure_search(
    smiles: str,
    limit: int = 100,
    molecular_weight_min: Optional[float] = None,
    molecular_weight_max: Optional[float] = None,
    clogp_min: Optional[float] = None,
    clogp_max: Optional[float] = None,
    lipinski_hbd_min: Optional[int] = None,
    lipinski_hbd_max: Optional[int] = None,
    tpsa_min: Optional[float] = None,
    tpsa_max: Optional[float] = None,
    rotatable_bonds_min: Optional[int] = None,
    rotatable_bonds_max: Optional[int] = None,
    heavy_atoms_min: Optional[int] = None,
    heavy_atoms_max: Optional[int] = None,
    aromatic_rings_min: Optional[int] = None,
    aromatic_rings_max: Optional[int] = None,
    rings_min: Optional[int] = None,
    rings_max: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info(f"Initiating substructure search for smiles: {smiles}")
        # Prepare a dictionary of filters with non-None values
        filters = {
            "molecular_weight_min": molecular_weight_min,
            "molecular_weight_max": molecular_weight_max,
            "clogp_min": clogp_min,
            "clogp_max": clogp_max,
            "lipinski_hbd_min": lipinski_hbd_min,
            "lipinski_hbd_max": lipinski_hbd_max,
            "tpsa_min": tpsa_min,
            "tpsa_max": tpsa_max,
            "rotatable_bonds_min": rotatable_bonds_min,
            "rotatable_bonds_max": rotatable_bonds_max,
            "heavy_atoms_min": heavy_atoms_min,
            "heavy_atoms_max": heavy_atoms_max,
            "aromatic_rings_min": aromatic_rings_min,
            "aromatic_rings_max": aromatic_rings_max,
            "rings_min": rings_min,
            "rings_max": rings_max,
        }

        # Clean the dictionary by removing filters that are None
        filters = {k: v for k, v in filters.items() if v is not None}
        # Call the repository function to execute the substructure search
        results = await molecule_repo.search_substructure_molecules(
            db=db, query_smiles=smiles, limit=limit, filters=filters
        )

        if not results:
            logger.warning(f"No molecules found with substructure: {smiles}")
        else:
            logger.info(f"Substructure search completed with {len(results)} results")

        return results

    except Exception as e:
        logger.error(f"Error performing substructure search: {e}")
        # Raise a detailed HTTP exception with a 500 status code
        raise HTTPException(
            status_code=500,
            detail="An error occurred while performing the substructure search",
        )


@router.get("/substructure-multiple", response_model=List[MoleculeBase])
async def substructure_search_all(
    smiles_list: List[str] = Query(...),
    condition: str = Query(...),
    limit: int = 100,
    molecular_weight_min: Optional[float] = None,
    molecular_weight_max: Optional[float] = None,
    clogp_min: Optional[float] = None,
    clogp_max: Optional[float] = None,
    lipinski_hbd_min: Optional[int] = None,
    lipinski_hbd_max: Optional[int] = None,
    tpsa_min: Optional[float] = None,
    tpsa_max: Optional[float] = None,
    rotatable_bonds_min: Optional[int] = None,
    rotatable_bonds_max: Optional[int] = None,
    heavy_atoms_min: Optional[int] = None,
    heavy_atoms_max: Optional[int] = None,
    aromatic_rings_min: Optional[int] = None,
    aromatic_rings_max: Optional[int] = None,
    rings_min: Optional[int] = None,
    rings_max: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    API endpoint for substructure search where all substructures must be found in the molecule.
    Accepts a list of SMILES strings and searches for molecules in the database that contain
    all of the substructures.

    Args:
        smiles_list (List[str]): A list of SMILES strings representing the query molecules.
        db (AsyncSession): Database session (provided by dependency injection).

    Returns:
        List[Dict[str, Any]]: A list of molecules that match all substructures.
    """
    try:
        # Perform substructure search where all substructures are present
        filters = {
            "molecular_weight_min": molecular_weight_min,
            "molecular_weight_max": molecular_weight_max,
            "clogp_min": clogp_min,
            "clogp_max": clogp_max,
            "lipinski_hbd_min": lipinski_hbd_min,
            "lipinski_hbd_max": lipinski_hbd_max,
            "tpsa_min": tpsa_min,
            "tpsa_max": tpsa_max,
            "rotatable_bonds_min": rotatable_bonds_min,
            "rotatable_bonds_max": rotatable_bonds_max,
            "heavy_atoms_min": heavy_atoms_min,
            "heavy_atoms_max": heavy_atoms_max,
            "aromatic_rings_min": aromatic_rings_min,
            "aromatic_rings_max": aromatic_rings_max,
            "rings_min": rings_min,
            "rings_max": rings_max,
        }

        # Clean the dictionary by removing filters that are None
        filters = {k: v for k, v in filters.items() if v is not None}

        results = await search_substructure_multiple(
            db=db,
            smiles_list=smiles_list,
            condition=condition,
            limit=limit,
            filters=filters,
        )

        return results

    except ValueError as ve:
        logger.error(f"Invalid SMILES string: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in substructure search: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while performing the substructure search",
        )


# Batch
@router.post("/batch", response_model=List[MoleculeBase])
async def create_molecules_batch(molecules: List[InputMoleculeDto]):
    try:
        logger.info(f"Creating batch of {len(molecules)} molecules")

        result = await batch_registration.register_molecules_batch(molecules)

        logger.debug(f"Batch creation successful for {len(molecules)} molecules")
        return result

    except ValueError as ve:
        logger.error(f"Invalid molecule data: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule data: {ve}")
    except Exception as e:
        logger.error(f"Error creating molecules: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/batch-create-parents")
async def batch_create_parents(background_tasks: BackgroundTasks):
    """
    Endpoint to trigger a background job for batch processing molecules to create parents.
    """
    try:
        logger.info(
            "Received request to trigger background job for batch creating parent molecules."
        )

        # Add the background task to process molecule parents in batches
        background_tasks.add_task(process_all_molecule_batches)

        return {
            "message": "Batch parent creation job started successfully. Check logs for progress."
        }

    except Exception as e:
        logger.error(f"Error starting batch parent creation job: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start batch parent creation job."
        )
