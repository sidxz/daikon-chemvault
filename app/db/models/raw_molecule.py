from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class RawMolecule(Base):
    __tablename__ = "raw_molecules"

    id = Column(Integer, primary_key=True, index=True)
    registration_id = Column(UUID(as_uuid=True), index=True, unique=False, nullable=False)
    name = Column(String, index=True)
    smiles = Column(String)
    reg_status = Column(String) # NEW, DUPLICATE, ERROR

    
    def __repr__(self):
        return f"id: {self.id}, name: {self.name}"

