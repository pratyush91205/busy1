"""Shared paging shapes.

Written once here against vehicles so that the service listing in Phase 12 gets
the same contract rather than a second one that differs in small ways.
"""

from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class PageParams(BaseModel):
    """Page number and size, as a query-parameter model.

    ``limit`` is capped rather than unbounded: an open ``limit`` is how a list
    endpoint becomes an accidental full-table export.
    """

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    total_pages: int

    @classmethod
    def build(cls, items: list[T], total: int, params: PageParams) -> Page[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            limit=params.limit,
            # A page past the end is an empty list, not an error: a client that
            # deletes the last row on page 3 should see an empty page 3, not a
            # 404 it has to special-case.
            total_pages=ceil(total / params.limit) if total else 0,
        )
