from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.repositories import molecule as molecule_repo
from app.schemas import molecule as schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Molecule)
def create_molecule(molecule: schemas.MoleculeCreate, db: Session = Depends(get_db)):
    return molecule_repo.create_molecule(db=db, molecule=molecule)

@router.get("/{molecule_id}", response_model=schemas.Molecule)
def read_molecule(molecule_id: int, db: Session = Depends(get_db)):
    db_molecule = molecule_repo.get_molecule(db=db, molecule_id=molecule_id)
    if db_molecule is None:
        raise HTTPException(status_code=404, detail="Molecule not found")
    return db_molecule

@router.put("/{molecule_id}", response_model=schemas.Molecule)
def update_molecule(molecule_id: int, molecule: schemas.MoleculeUpdate, db: Session = Depends(get_db)):
    return molecule_repo.update_molecule(db=db, molecule_id=molecule_id, molecule=molecule)

@router.delete("/{molecule_id}")
def delete_molecule(molecule_id: int, db: Session = Depends(get_db)):
    molecule_repo.delete_molecule(db=db, molecule_id=molecule_id)
    return {"detail": "Molecule deleted"}
