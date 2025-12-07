"""Top-level API router registration."""

from fastapi import APIRouter

from app.api.v1 import batch, config, molcal, molecule

api_router = APIRouter()

api_router.include_router(molecule.router, prefix="/molecules", tags=["molecules"])
api_router.include_router(molcal.router, prefix="/molcal", tags=["molcal"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(batch.router, prefix="/batch", tags=["batch"])

