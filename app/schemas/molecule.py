from pydantic import BaseModel, ConfigDict

class MoleculeBase(BaseModel):
    name: str
    formula: str
    molecular_weight: str

class MoleculeCreate(MoleculeBase):
    pass

class MoleculeUpdate(MoleculeBase):
    pass

class Molecule(MoleculeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
