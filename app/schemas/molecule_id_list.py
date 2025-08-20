from pydantic import BaseModel
from typing import List
from uuid import UUID

class MoleculeIdList(BaseModel):
    ids: List[UUID]