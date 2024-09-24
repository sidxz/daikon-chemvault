from pydantic import BaseModel, Field, UUID4
from typing import Optional


# Base schema for shared attributes between create, update, and read operations
class ParentMoleculeBase(BaseModel):
    id: Optional[UUID4] = None
    name: Optional[str] = None
    synonyms: Optional[str] = None
    smiles_canonical: Optional[str] = None
    selfies: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    smarts: Optional[str] = None
    
    mw: Optional[float] = Field(default=0.0)
    iupac_name: Optional[str] = None
    formula: Optional[str] = None
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
    
    molblock: Optional[str] = None


# Schema for creating a new molecule; inherits from MoleculeBase
class ParentMoleculeCreate(ParentMoleculeBase):
    id: UUID4 = Field(default_factory=UUID4)
    smiles: str  # Required field for molecule creation


# Schema for updating an existing molecule; inherits from MoleculeBase
class ParentMoleculeUpdate(ParentMoleculeBase):
    pass


# Schema for reading a molecule from the database, includes the ID
class ParentMoleculeRead(ParentMoleculeBase):
    id: UUID4
    

    class Config:
        orm_mode = True
