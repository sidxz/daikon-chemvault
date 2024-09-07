from pydantic import UUID4, BaseModel, ConfigDict
from typing import Optional

class InputMoleculeDto(BaseModel):
    id: Optional[UUID4] = None
    name: str
    smiles: str
