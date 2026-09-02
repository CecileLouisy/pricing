"""Types métier partagés par tout le domaine."""

from enum import Enum


class Mode(str, Enum):
    """Contexte tarifaire d'un stationnement."""

    RESERVED = "reserved"
    WALK_IN = "walk_in"


# Zones initiales connues à la mise en service.
# Nouvelles zones ajoutables dynamiquement via POST /rates (stockées en base).
INITIAL_ZONES: tuple[str, ...] = (
    "standard",
    "xl",
    "disabled",
    "electric",
    "two_wheels",
)

MAX_DURATION_MIN: int = 7 * 24 * 60  # 10 080 min = 7 jours
