from pydantic import BaseModel, ConfigDict


# Base schema for shared attributes between create, update, and read operations
class MoleculeBase(BaseModel):
    name: str
    formula: str
    molecular_weight: str


# Schema for creating a new molecule; inherits from MoleculeBase
class MoleculeCreate(MoleculeBase):
    pass


# Schema for updating an existing molecule; inherits from MoleculeBase
class MoleculeUpdate(MoleculeBase):
    pass


# Schema for reading a molecule from the database, includes the ID
class Molecule(MoleculeBase):
    id: int

    # ConfigDict used to allow Pydantic to create a model from an ORM instance or dict-like object
    model_config = ConfigDict(from_attributes=True)
