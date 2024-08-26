from fastapi import FastAPI
from app.api.v1 import molecule
from app.core.logging_config import logger  # Import the configured logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    logger.info("Application startup")
    yield
    # Shutdown code
    logger.info("Application shutdown")

app = FastAPI(lifespan=lifespan)

# Include the molecule router
app.include_router(molecule.router, prefix="/molecules", tags=["molecules"])

