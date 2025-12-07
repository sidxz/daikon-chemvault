from pydantic import BaseModel, ConfigDict, UUID4, Field
from typing import Optional, List

class PainsBase(BaseModel):
    """
    Base schema for PAINS results, used as a foundation for Create, Update, and Read operations.
    """
    id: UUID4  # Foreign key referencing the Molecule ID
    rdkit_pains: bool = Field(default=False, description="Indicates whether the molecule contains PAINS alerts")
    rdkit_pains_label: Optional[List[str]] = Field(default=None, description="List of PAINS categories detected")

class PainsCreate(PainsBase):
    """
    Schema for creating a new PAINS entry.
    """
    pass  # No extra fields needed for creation

class PainsUpdate(BaseModel):
    """
    Schema for updating an existing PAINS entry.
    """
    rdkit_pains: Optional[bool] = None
    rdkit_pains_label: Optional[List[str]] = None

class PainsRead(PainsBase):
    """
    Schema for reading PAINS data from the database.
    """
    model_config = ConfigDict(from_attributes=True)
