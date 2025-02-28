from pydantic import UUID4, BaseModel, ConfigDict
from typing import List, Optional

class PainsInputDto(BaseModel):
    id: UUID4
    name: Optional[str] = None
    smiles: str

class PainsOutputDto(BaseModel):
    id: UUID4
    name: Optional[str] = None
    smiles: str
    rdkit_pains: Optional[bool]
    rdkit_pains_label: Optional[List[str]] = None