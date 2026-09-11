"""Application factory.

``get_settings()`` runs while this module is imported, so an invalid
environment stops the process at startup instead of surfacing as a 500 on the
first request.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


async def handle_database_error(request: Request, exc: Exception) -> JSONResponse:
    """Turn an unreachable database into 503 rather than a bare 500."""
    logger.exception("Database error handling %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "database": "unreachable"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="Fleet Maintenance API", version="0.1.0")

    # Routes read settings off the app rather than the process-wide cache,
    # so the settings passed here are the ones actually used - including the
    # key tokens are verified against.
    app.state.settings = settings

    # Only the configured origins are allowed. The settings validator rejects
    # "*", so a wildcard can never be combined with credentialed requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(SQLAlchemyError, handle_database_error)
    app.include_router(api_router)
    return app


app = create_app()
