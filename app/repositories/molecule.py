from sqlalchemy.orm import Session
from app.db.models.molecule import Molecule
from app.schemas.molecule import MoleculeCreate, MoleculeUpdate

def get_molecule(db: Session, molecule_id: int):
    return db.query(Molecule).filter(Molecule.id == molecule_id).first()

def create_molecule(db: Session, molecule: MoleculeCreate):
    db_molecule = Molecule(**molecule.model_dump())
    db.add(db_molecule)
    db.commit()
    db.refresh(db_molecule)
    return db_molecule

def update_molecule(db: Session, molecule_id: int, molecule: MoleculeUpdate):
    db_molecule = get_molecule(db, molecule_id)
    for key, value in molecule.model_dump().items():
        setattr(db_molecule, key, value)
    db.commit()
    return db_molecule

def delete_molecule(db: Session, molecule_id: int):
    db_molecule = get_molecule(db, molecule_id)
    db.delete(db_molecule)
    db.commit()
