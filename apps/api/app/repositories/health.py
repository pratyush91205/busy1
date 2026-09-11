"""Database access for the health check."""

from sqlalchemy import select
from sqlalchemy.orm import Session


def ping(db: Session) -> None:
    """Run the cheapest possible query.

    Raises ``SQLAlchemyError`` when the database cannot be reached, which is
    what makes the health check meaningful rather than a liveness probe of the
    web process.
    """
    db.execute(select(1))
