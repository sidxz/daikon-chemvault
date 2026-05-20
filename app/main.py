from fastapi import FastAPI, Request
from app.api.v1 import admet, batch, config, molcal, molecule  # Import the router for molecule-related endpoints
from app.core.logging_config import logger  # Import the configured logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.db.initializer import initialize_db
from app.middleware.logs.api_logs import log_requests
# Load environment variables from a .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code executed before the application starts
    logger.info("Application startup")
    logger.info("Initializing db")
    await initialize_db()
    logger.info("Ready to accept requests")
    yield
    # Shutdown code executed when the application is stopping
    logger.info("Application shutdown")


# Instantiate the FastAPI application with the custom lifespan context
app = FastAPI(lifespan=lifespan)


# Middleware to log requests
#app.middleware("http")(log_requests)


# Include routers
app.include_router(molecule.router, prefix="/molecules", tags=["molecules"])

app.include_router(molcal.router, prefix="/molcal", tags=["molcal"])

app.include_router(config.router, prefix="/config", tags=["config"])

app.include_router(batch.router, prefix="/batch", tags=["batch"])

app.include_router(admet.router, prefix="/admet", tags=["admet"])
