"""Health check.

Deliberately reports healthy only after touching the database. A check that
proves the web process is running, and nothing more, is what allows a service
with an unusable DATABASE_URL to sit in production looking green.
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.repositories import health as health_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health(db: DbSession) -> JSONResponse:
    try:
        health_repository.ping(db)
    except SQLAlchemyError:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unreachable"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "database": "ok"},
    )
