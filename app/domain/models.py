"""Entités et agrégats du domaine — dataclasses immutables."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.value_objects import Mode


@dataclass(frozen=True, slots=True)
class Rate:
    """Un tarif horaire pour une combinaison (zone, mode) dans une grille."""

    id: UUID
    grid_id: UUID
    zone: str
    mode: Mode
    hourly_rate_eur: Decimal


@dataclass(frozen=True, slots=True)
class PriceGrid:
    """Grille tarifaire versionnée.

    Une grille est immuable une fois publiée. Toute modification d'un tarif
    ou de la gratuité crée une nouvelle grille.
    """

    id: UUID
    version: int
    free_period_min: int
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    rates: tuple[Rate, ...] = field(default_factory=tuple)

    def find_rate(self, zone: str, mode: Mode) -> Rate | None:
        for rate in self.rates:
            if rate.zone == zone and rate.mode == mode:
                return rate
        return None


@dataclass(frozen=True, slots=True)
class Quote:
    """Un devis calculé, immuable, référence la grille utilisée."""

    id: UUID
    grid_id: UUID
    zone: str
    mode: Mode
    duration_min: int
    amount_eur: Decimal
    breakdown: dict
    computed_at: datetime
