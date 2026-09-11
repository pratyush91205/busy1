"""Domain models.

Every model is imported here so that importing this package populates
``Base.metadata`` completely - which is what Alembic compares against.
"""

from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.enums import AuditEventType, ServiceStatus, UserRole
from app.models.overdue_alert_dismissal import OverdueAlertDismissal
from app.models.service_note import ServiceNote
from app.models.service_record import ServiceRecord
from app.models.service_technician import ServiceTechnician
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "Base",
    "OverdueAlertDismissal",
    "ServiceNote",
    "ServiceRecord",
    "ServiceStatus",
    "ServiceTechnician",
    "User",
    "UserRole",
    "Vehicle",
]
