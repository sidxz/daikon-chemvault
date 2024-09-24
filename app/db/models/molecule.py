from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from sqlalchemy.types import UserDefinedType
from app.db.with_metadata import WithMetadata
from sqlalchemy.orm import relationship


class MolType(UserDefinedType):
    def get_col_spec(self):
        return "mol"


class BfpType(UserDefinedType):
    def get_col_spec(self):
        return "bfp"


class Molecule(Base, WithMetadata):
    __tablename__ = "molecules"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, unique=True, nullable=False
    )
    name = Column(String, index=True)
    synonyms = Column(String, index=True)
    smiles = Column(String)
    smiles_canonical = Column(String, index=True)
    selfies = Column(String)
    inchi = Column(String)
    inchi_key = Column(String)
    smarts = Column(String)
    mw = Column(Float)
    fsp3 = Column(Float)
    iupac_name = Column(String)
    formula = Column(String)
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
    n_aliphatic_heterocycles = Column(Integer)
    n_aliphatic_rings = Column(Integer)
    n_aromatic_carbocycles = Column(Integer)
    n_aromatic_heterocycles = Column(Integer)
    n_aromatic_rings = Column(Integer)
    n_saturated_carbocycles = Column(Integer)
    n_saturated_heterocycles = Column(Integer)
    n_saturated_rings = Column(Integer)
    ro5_compliant = Column(Boolean)
    o_molblock = Column(String)
    std_molblock = Column(String)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('parent_molecules.id'))
    morgan_fp = Column(BfpType(), index=True)
    rdkit_fp = Column(BfpType(), index=True)
    mol = Column(MolType(), index=True)

    # Establish a relationship to ParentMolecule
    parent_molecule = relationship("ParentMolecule", back_populates="children")
    
    def __repr__(self):
        return f"id: {self.id}, name: {self.name}, synonyms: {self.synonyms}"
