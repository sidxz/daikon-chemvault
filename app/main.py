from fastapi import Depends, FastAPI, Request
from app.api.v1 import admet, batch, config, molcal, molecule  # Import the router for molecule-related endpoints
from app.core.logging_config import logger  # Import the configured logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.db.initializer import initialize_db
from app.middleware.logs.api_logs import log_requests
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.auth import require_token
from app.core.config import settings
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
# openapi_url=None also turns off /docs and /redoc.
app = FastAPI(lifespan=lifespan, openapi_url="/openapi.json" if settings.ENABLE_DOCS else None)


# Middleware to log requests
#app.middleware("http")(log_requests)

app.add_middleware(SecurityHeadersMiddleware)


# Include routers. Every router requires a valid bearer token (see app/core/auth.py), except config:
# /config/health is polled anonymously by DAIKON's gateway.
auth = [Depends(require_token)]

app.include_router(molecule.router, prefix="/molecules", tags=["molecules"], dependencies=auth)

app.include_router(molcal.router, prefix="/molcal", tags=["molcal"], dependencies=auth)

app.include_router(config.router, prefix="/config", tags=["config"])

app.include_router(batch.router, prefix="/batch", tags=["batch"], dependencies=auth)

app.include_router(admet.router, prefix="/admet", tags=["admet"], dependencies=auth)
