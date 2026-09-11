"""The walking skeleton's one table.

It exists to prove the migration chain and the database read path end to end.
The real domain schema arrives in Phase 3, which removes this table.
"""

from datetime import datetime

from sqlalchemy import DateTime, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeploymentCheck(Base):
    __tablename__ = "deployment_check"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
