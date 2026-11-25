"""Correlation ID of the request being processed, shared by the HTTP layer and the logs.

The ID is an opaque technical identifier (never personal data). It is received from
the calling service (Booking, Access) in the X-Correlation-ID header, or generated
when the caller does not send one.
"""

import re
from contextvars import ContextVar
from uuid import uuid4

HEADER = "X-Correlation-ID"

# Letters, digits, "-" and "_" only: no spaces or line breaks that could break
# the key=value log format or inject fake log lines.
_VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")

_current_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def is_valid(value: str) -> bool:
    return _VALID_ID.fullmatch(value) is not None


def new_correlation_id() -> str:
    return str(uuid4())


def get_correlation_id() -> str | None:
    """Correlation ID of the current request, or None outside a request."""
    return _current_id.get()


def set_correlation_id(value: str) -> None:
    _current_id.set(value)
