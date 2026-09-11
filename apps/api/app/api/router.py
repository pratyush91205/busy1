"""Aggregates every route module into one router the app includes."""

from fastapi import APIRouter

from app.api.routes import (
    alerts,
    auth,
    dashboard,
    health,
    reports,
    services,
    technicians,
    vehicles,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
# Before the service routes: FastAPI matches in registration order, so
# /services/export.csv has to be declared ahead of /services/{service_id}
# or it is read as a service with the id "export.csv".
api_router.include_router(reports.router)
api_router.include_router(vehicles.router)
api_router.include_router(services.router)
api_router.include_router(technicians.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
