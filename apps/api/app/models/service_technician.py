"""Technician assignments: many-to-many between service records and users.

A join table rather than a list column, so a technician's own record list is a
server-side query and a duplicate assignment is a database error.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServiceTechnician(Base):
    __tablename__ = "service_technicians"

    service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "service_records.id", ondelete="RESTRICT", name="fk_service_technicians_service_id"
        ),
        primary_key=True,
    )
    technician_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_service_technicians_technician_id"),
        primary_key=True,
        # Lookups by service_id are already served by the leading column of the
        # composite primary key; this index is the one the technician's own
        # "my assigned records" query needs.
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
