from pydantic import BaseModel, ConfigDict, Field, UUID4
from typing import Optional

from app.schemas.molecule import MoleculeBase


class SimilarMoleculeDto(MoleculeBase):
    similarity: float

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={UUID4: lambda v: str(v)},
    )
