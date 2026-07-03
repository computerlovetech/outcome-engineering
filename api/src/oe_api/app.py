"""FastAPI application factory. The API is the single read/write path;
CLI, MCP, and the frontend are all HTTP clients of this app."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oe_api.routes import flywheel, graphs, nodes, system
from oe_api.settings import Settings, get_settings
from oe_core.errors import (
    AmbiguousSelectorError,
    CascadeRequiredError,
    DomainError,
    NotFoundError,
    VersionConflictError,
)
from oe_store.db import make_engine, make_session_factory, run_migrations

STATUS_FOR_ERROR = (
    (NotFoundError, 404),
    (VersionConflictError, 409),
    (AmbiguousSelectorError, 409),
    (CascadeRequiredError, 409),
    (DomainError, 400),
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.run_migrations_on_startup:
            run_migrations(settings.database_url)
        if not hasattr(app.state, "session_factory"):
            app.state.session_factory = make_session_factory(make_engine(settings.database_url))
        yield

    app = FastAPI(title="Outcome Engineering API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
        for error_type, status in STATUS_FOR_ERROR:
            if isinstance(error, error_type):
                return JSONResponse(status_code=status, content={"detail": str(error)})
        return JSONResponse(status_code=400, content={"detail": str(error)})

    prefix = "/api"
    app.include_router(system.router, prefix=prefix)
    app.include_router(graphs.router, prefix=prefix)
    app.include_router(nodes.router, prefix=prefix)
    app.include_router(flywheel.router, prefix=prefix)
    return app


def main() -> FastAPI:
    return create_app()
