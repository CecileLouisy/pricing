"""Value types shared across the domain."""

from enum import Enum


class Mode(str, Enum):
    """Pricing context for a parking session."""

    RESERVED = "reserved"
    WALK_IN = "walk_in"


# Zones seeded at first startup.
# New zones can be added dynamically via POST /rates (stored in the database).
INITIAL_ZONES: tuple[str, ...] = (
    "standard",
    "xl",
    "disabled",
    "electric",
    "two_wheels",
)

MAX_DURATION_MIN: int = 7 * 24 * 60  # 10,080 min = 7 days
