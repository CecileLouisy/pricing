"""Règles pures de calcul du prix.

Ces fonctions ne dépendent de rien — pas de DB, pas de HTTP, pas de datetime.now.
Elles sont directement testables unitairement.
"""

import math
from decimal import ROUND_HALF_UP, Decimal

from app.domain.errors import InvalidDuration
from app.domain.value_objects import MAX_DURATION_MIN

_CENTS = Decimal("0.01")


def _validate_duration(duration_min: int) -> None:
    if duration_min <= 0 or duration_min > MAX_DURATION_MIN:
        raise InvalidDuration(
            f"duration_min must be in (0, {MAX_DURATION_MIN}], got {duration_min}"
        )


def compute_walk_in(
    duration_min: int,
    free_period_min: int,
    hourly_rate_eur: Decimal,
) -> tuple[Decimal, dict]:
    """Facturation au quart d'heure entamé, avec période initiale gratuite."""
    _validate_duration(duration_min)
    billable_min = max(0, duration_min - free_period_min)
    quarters = math.ceil(billable_min / 15)
    quarter_rate = hourly_rate_eur / Decimal(4)
    amount = (Decimal(quarters) * quarter_rate).quantize(_CENTS, rounding=ROUND_HALF_UP)
    breakdown = {
        "duration_min": duration_min,
        "free_min": free_period_min,
        "billable_min": billable_min,
        "quarters": quarters,
        "hourly_rate_eur": str(hourly_rate_eur),
    }
    return amount, breakdown


def compute_reserved(
    duration_min: int,
    hourly_rate_eur: Decimal,
) -> tuple[Decimal, dict]:
    """Facturation à l'heure pleine (durée garantie multiple de 60 par Booking)."""
    _validate_duration(duration_min)
    if duration_min % 60 != 0:
        raise InvalidDuration(
            f"reserved mode requires duration_min to be a multiple of 60, got {duration_min}"
        )
    hours = duration_min // 60
    amount = (Decimal(hours) * hourly_rate_eur).quantize(_CENTS, rounding=ROUND_HALF_UP)
    breakdown = {
        "duration_min": duration_min,
        "hours": hours,
        "hourly_rate_eur": str(hourly_rate_eur),
    }
    return amount, breakdown
