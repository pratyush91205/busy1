"""Database access for the deployment_check table."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deployment_check import DeploymentCheck


def get_row(db: Session) -> DeploymentCheck | None:
    """The seeded row, or None when the table is empty."""
    statement = select(DeploymentCheck).order_by(DeploymentCheck.id).limit(1)
    return db.execute(statement).scalar_one_or_none()
