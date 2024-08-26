from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Molecule(Base):
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    formula = Column(String)
    molecular_weight = Column(String)
    
    def __repr__(self):
        return f"id: {self.id}, name: {self.name}"

