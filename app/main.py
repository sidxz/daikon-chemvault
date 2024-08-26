from fastapi import FastAPI
from app.api.v1 import molecule  # Import the router for molecule-related endpoints
from app.core.logging_config import logger  # Import the configured logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from a .env file
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code executed before the application starts
    logger.info("Application startup")
    logger.info("Initializing db")
    # initialize_db()  # Uncomment this line when the initialize_db function is ready
    logger.info("Ready to accept requests")
    yield
    # Shutdown code executed when the application is stopping
    logger.info("Application shutdown")


# Instantiate the FastAPI application with the custom lifespan context
app = FastAPI(lifespan=lifespan)

# Include the molecule router with a specific prefix and tag
app.include_router(molecule.router, prefix="/molecules", tags=["molecules"])
