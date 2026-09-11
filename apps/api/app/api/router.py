"""Aggregates every route module into one router the app includes."""

from fastapi import APIRouter

from app.api.routes import auth, health, services, technicians, vehicles

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(vehicles.router)
api_router.include_router(services.router)
api_router.include_router(technicians.router)
