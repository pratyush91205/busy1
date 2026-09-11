"""Text normalisation shared by the request schemas.

``min_length=1`` alone is not enough for a field the database also guards with
``char_length(btrim(...)) > 0``: "   " is three characters, passes Pydantic,
strips to nothing, and reaches PostgreSQL as a CheckViolation - which surfaces
as a 503 rather than the 422 the client deserves.

Stripping *before* the length check closes that gap, so the constraint stays
the guarantee and the schema stays the readable rejection.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator

# Leading and trailing whitespace removed.
Stripped = Annotated[str, BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v)]

# As above, and runs of whitespace inside collapse to a single space. For
# identifiers where "VAN  001" and "VAN 001" must not be two different things.
Collapsed = Annotated[
    str, BeforeValidator(lambda v: " ".join(v.split()) if isinstance(v, str) else v)
]
