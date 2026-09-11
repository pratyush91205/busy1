"""Domain errors the service layer raises, and the status codes they mean.

The service layer must not import FastAPI - a business rule is not an HTTP
concern, and rules that raise HTTPException cannot be tested without a request.
So services raise these, one exception handler in ``main`` turns them into
responses, and route handlers stay free of try/except.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for every rule the service layer enforces."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """The resource does not exist. 404."""

    status_code = 404


class ConflictError(DomainError):
    """The request is well formed but the rules refuse it. 409.

    Duplicate registration, an odometer moving backwards, an invalid lifecycle
    transition, editing an archived vehicle.
    """

    status_code = 409


class ForbiddenError(DomainError):
    """Authenticated, but not allowed this particular resource. 403.

    For the per-resource rules ``require_role`` cannot express - a technician
    holding a valid token reaching for a record they are not assigned to.
    """

    status_code = 403
