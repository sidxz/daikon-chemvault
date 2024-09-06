from pydantic import BaseModel, Field, UUID4
from typing import Optional


# Base schema for shared attributes between create, update, and read operations
class MoleculeBase(BaseModel):
    id: Optional[UUID4] = None
    name: Optional[str] = None
    synonyms: Optional[str] = None
    smiles: Optional[str] = None
    smiles_canonical: Optional[str] = None
    selfies: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    smarts: Optional[str] = None
    o_molblock: Optional[str] = None
    std_molblock: Optional[str] = None
    parent_id: Optional[UUID4] = None
    mw: Optional[float] = Field(default=0.0)
    fsp3: Optional[float] = Field(default=0.0)
    n_lipinski_hba: Optional[int] = Field(default=0)
    n_lipinski_hbd: Optional[int] = Field(default=0)
    n_rings: Optional[int] = Field(default=0)
    n_hetero_atoms: Optional[int] = Field(default=0)
    n_heavy_atoms: Optional[int] = Field(default=0)
    n_rotatable_bonds: Optional[int] = Field(default=0)
    n_radical_electrons: Optional[int] = Field(default=0)
    tpsa: Optional[float] = Field(default=0.0)
    qed: Optional[float] = Field(default=0.0)
    clogp: Optional[float] = Field(default=0.0)
    sas: Optional[float] = Field(default=0.0)
    n_aliphatic_carbocycles: Optional[int] = Field(default=0)
    n_aliphatic_heterocycles: Optional[int] = Field(default=0)
    n_aliphatic_rings: Optional[int] = Field(default=0)
    n_aromatic_carbocycles: Optional[int] = Field(default=0)
    n_aromatic_heterocycles: Optional[int] = Field(default=0)
    n_aromatic_rings: Optional[int] = Field(default=0)
    n_saturated_carbocycles: Optional[int] = Field(default=0)
    n_saturated_heterocycles: Optional[int] = Field(default=0)
    n_saturated_rings: Optional[int] = Field(default=0)
    ro5_compliant: Optional[bool] = Field(default=False)


# Schema for creating a new molecule; inherits from MoleculeBase
class MoleculeCreate(MoleculeBase):
    id: UUID4 = Field(default_factory=UUID4)
    smiles: str  # Required field for molecule creation


# Schema for updating an existing molecule; inherits from MoleculeBase
class MoleculeUpdate(MoleculeBase):
    pass


# Schema for reading a molecule from the database, includes the ID
class MoleculeRead(MoleculeBase):
    id: UUID4
    morgan_fp: Optional[str] = None  # You may need a custom serialization for BfpType
    mol: Optional[str] = None  # You may need a custom serialization for MolType

    class Config:
        orm_mode = True
