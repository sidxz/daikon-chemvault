from pydantic import UUID4, BaseModel, ConfigDict
from typing import Optional

class ClusterInputDto(BaseModel):
    id: UUID4
    name: Optional[str] = None
    smiles: str

class ClusterOutputDto(BaseModel):
    id: UUID4
    name: Optional[str] = None
    smiles: str
    cluster: int
    centroid: bool