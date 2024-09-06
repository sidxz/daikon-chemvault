from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from sqlalchemy.types import UserDefinedType


class MolType(UserDefinedType):
    def get_col_spec(self):
        return "mol"


class BfpType(UserDefinedType):
    def get_col_spec(self):
        return "bfp"


class ParentMolecule(Base):
    __tablename__ = "parent_molecules"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, unique=True, nullable=False
    )
    name = Column(String, index=True)
    synonyms = Column(String, index=True)
    smiles_canonical = Column(String, index=True)
    selfies = Column(String)
    inchi = Column(String)
    inchi_key = Column(String)
    smarts = Column(String)
    molblock = Column(String)
    morgan_fp = Column(BfpType(), index=True)
    mol = Column(MolType(), index=True)
    mw = Column(Float)
    fsp3 = Column(Float)
    n_lipinski_hba = Column(Integer)
    n_lipinski_hbd = Column(Integer)
    n_rings = Column(Integer)
    n_hetero_atoms = Column(Integer)
    n_heavy_atoms = Column(Integer)
    n_rotatable_bonds = Column(Integer)
    n_radical_electrons = Column(Integer)
    tpsa = Column(Float)
    qed = Column(Float)
    clogp = Column(Float)
    sas = Column(Float)
    n_aliphatic_carbocycles = Column(Integer)
    n_aliphatic_heterocyles = Column(Integer)
    n_aliphatic_rings = Column(Integer)
    n_aromatic_carbocycles = Column(Integer)
    n_aromatic_heterocyles = Column(Integer)
    n_aromatic_rings = Column(Integer)
    n_saturated_carbocycles = Column(Integer)
    n_saturated_heterocyles = Column(Integer)
    n_saturated_rings = Column(Integer)
    ro5_compliant = Column(Boolean)

    def __repr__(self):
        return f"id: {self.id}, name: {self.name}"
