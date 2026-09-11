"""API contract for the deployment check row."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeploymentCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    checked_at: datetime
