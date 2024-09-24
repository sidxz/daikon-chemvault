from pydantic import BaseModel, Field, UUID4
from typing import Optional

from app.schemas.molecule import MoleculeBase


class SimilarMoleculeDto(MoleculeBase):
    similarity: float

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        json_encoders = {
            UUID4: lambda v: str(v),
        }
