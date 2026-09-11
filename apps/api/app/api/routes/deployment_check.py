"""Deployment check read path: route -> repository -> database."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.models.deployment_check import DeploymentCheck
from app.repositories import deployment_check as deployment_check_repository
from app.schemas.deployment_check import DeploymentCheckRead

router = APIRouter(prefix="/api", tags=["deployment-check"])


@router.get("/deployment-check", response_model=DeploymentCheckRead)
def read_deployment_check(db: DbSession) -> DeploymentCheck:
    row = deployment_check_repository.get_row(db)
    if row is None:
        # An empty table means the migration ran but its seed did not, which is
        # a deployment fault worth naming rather than a 200 with a null body.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "deployment_check is empty. Migration 0001_deployment_check "
                "seeds exactly one row; run 'alembic upgrade head' against "
                "this database."
            ),
        )
    return row
