"""Application factory. Run with:  uvicorn app.main:create_app --factory --no-access-log

STATUS: not executed in the build sandbox (FastAPI/uvicorn are not installed there).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .api.errors import install_exception_handlers
from .api.middleware import install_middleware
from .api.v1.routes import router as v1_router
from .config import Settings
from .core.logging import configure_logging
from .runtime import Container

DESCRIPTION = (
    "Neural machine translation and multilingual NLP for English and Indian languages. "
    "Every response says which model produced it, under which licence, and whether a pivot was used. "
    "No endpoint returns a confidence score, because none of the models provides a calibrated one."
)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    if container is None:
        settings = settings or Settings()
        configure_logging(settings.log_level, json_output=settings.log_json)
        container = Container(settings.to_runtime())
        cors_origins, max_request_bytes = settings.cors_origin_list, settings.max_request_bytes
    else:
        cors_origins = settings.cors_origin_list if settings else ["http://localhost:5173"]
        max_request_bytes = settings.max_request_bytes if settings else 1_000_000

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container.start()
        try:
            yield
        finally:
            container.stop()

    app = FastAPI(
        title="Multilingual AI Intelligence Platform",
        version=__version__,
        description=DESCRIPTION,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.container = container
    install_middleware(app, cors_origins=cors_origins, max_request_bytes=max_request_bytes)
    install_exception_handlers(app)
    app.include_router(v1_router)
    return app
