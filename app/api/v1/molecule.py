from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import SessionLocal
from app.repositories import molecule as molecule_repo
from app.schemas.molecule_dto import InputMoleculeDto
from app.core.logging_config import logger
from app.services.molecule import registration
from app.schemas.molecule import MoleculeBase
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
        #result = await molecule_repo.create_molecule(db=db, molecule=molecule)
        result = await registration.register(molecule, db)
        logger.debug(f"Molecule created successfully: {result}")
        return result
    
    except ValueError as ve:
        logger.error(f"Invalid molecule data: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid molecule data: {ve}")
    except Exception as e:
        logger.error(f"Error creating molecule: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.get("/{molecule_id}", response_model=schemas.Molecule)
# async def read_molecule(molecule_id: int, db: AsyncSession = Depends(get_db)):
#     try:
#         logger.info(f"Fetching molecule with ID: {molecule_id}")
#         db_molecule = await molecule_repo.get_molecule(db=db, molecule_id=molecule_id)
#         if db_molecule is None:
#             logger.warning(f"Molecule with ID {molecule_id} not found")
#             raise HTTPException(status_code=404, detail="Molecule not found")
#         logger.debug(f"Molecule fetched successfully: {db_molecule}")
#         return db_molecule
#     except HTTPException as e:
#         raise e  # Re-raise HTTPException without modification
#     except Exception as e:
#         logger.error(f"Error fetching molecule with ID {molecule_id}: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


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
