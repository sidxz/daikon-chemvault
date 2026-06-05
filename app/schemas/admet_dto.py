from pydantic import UUID4, BaseModel
from typing import Any, Optional, Dict


class AdmetCalcResultDto(BaseModel):
    """Stateless ADMET calculation result for a single SMILES.

    Returned by POST /admet/predict, which does not persist anything; storage
    happens via inline-trigger on molecule registration and via /admet/backfill.
    """
    smiles: str
    predictions: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    error: Optional[str] = None


class AdmetPredictionDto(BaseModel):
    """Persisted ADMET prediction for a registered molecule. Returned by
    GET /admet/{id} and POST /admet/by-ids, and embedded inside MoleculeRead
    when fetching molecules by id."""
    id: UUID4
    status: str
    predictions: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    error: Optional[str] = None

    class Config:
        orm_mode = True
