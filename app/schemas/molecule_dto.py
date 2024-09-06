from pydantic import BaseModel, ConfigDict

class InputMoleculeDto(BaseModel):
    name: str
    smiles: str
