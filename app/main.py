"""FastAPI application entrypoint.

The global ``app`` is provided for ASGI servers. ``create_app`` can be used by
external tools (tests, scripts) to instantiate a fully configured application
instance.
"""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
