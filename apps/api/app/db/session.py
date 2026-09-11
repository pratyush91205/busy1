"""Database engine, session factory and the FastAPI session dependency."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(url: str) -> Engine:
    """Create an engine for ``url``.

    Supabase's transaction pooler (pgbouncer) cannot keep the server-side
    prepared statements psycopg creates by default, so they are disabled. The
    pre-ping costs one round trip and saves the first request after a free-tier
    idle connection has been closed underneath us.
    """
    connect_args: dict[str, object] = {}
    if url.startswith("postgresql+psycopg://"):
        connect_args["prepare_threshold"] = None
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Yield one session per request, closed when the request ends."""
    with get_session_factory()() as session:
        yield session
