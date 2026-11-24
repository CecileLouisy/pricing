"""Value types shared across the domain."""

from enum import StrEnum


class Mode(StrEnum):
    """Pricing context for a parking session."""

    RESERVED = "reserved"
    WALK_IN = "walk_in"


# Zones seeded at first startup, aligned on the Parking service categories
# (STANDARD, HANDICAPPED, ELECTRIC, XL, TWO_WHEELS) and stored in lowercase.
# New zones can be added dynamically via POST /rates (stored in the database).
INITIAL_ZONES: tuple[str, ...] = (
    "standard",
    "handicapped",
    "electric",
    "xl",
    "two_wheels",
)

# Zone renames applied to the active grid at startup (old code -> new code).
# Each one publishes a new grid version once, then does nothing on later startups.
ZONE_RENAMES: dict[str, str] = {"disabled": "handicapped"}


def normalize_zone(zone: str) -> str:
    """Make zone codes case-insensitive: "HANDICAPPED" == "handicapped"."""
    return zone.strip().lower()


MAX_DURATION_MIN: int = 7 * 24 * 60  # 10,080 min = 7 days
