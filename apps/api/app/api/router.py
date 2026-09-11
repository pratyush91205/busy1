"""Aggregates every route module into one router the app includes."""

from fastapi import APIRouter

from app.api.routes import deployment_check, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(deployment_check.router)
