"""The technician roster.

Needed so a fleet manager can pick someone to assign. Deliberately narrow: it
lists technicians only, returns the same public fields as everywhere else, and
has no create, update or delete - users come from ``scripts/create_user.py``,
and no route anywhere accepts a role.
"""

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.routes.vehicles import Manager
from app.repositories import user as user_repository
from app.schemas.service import UserSummary

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("", response_model=list[UserSummary])
def list_technicians(db: DbSession, _: Manager) -> list[UserSummary]:
    """Every technician, for the assignment picker.

    Manager-only: a technician cannot assign anyone, so the roster is not
    theirs to browse.
    """
    return [
        UserSummary.model_validate(user)
        for user in user_repository.list_technicians(db)
    ]
