"""Domain entities and aggregates — immutable dataclasses."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.value_objects import Mode


@dataclass(frozen=True, slots=True)
class Rate:
    """Hourly rate for a (zone, mode) combination within a grid.

    Identified by a random UUID (v4): a rate has no time semantics of its own,
    it belongs to the grid that carries the effective dates.
    """

    id: UUID
    grid_id: UUID
    zone: str
    mode: Mode
    hourly_rate_eur: Decimal


@dataclass(frozen=True, slots=True)
class PriceGrid:
    """Versioned price grid.

    A grid is immutable once published. Any change to a rate or the free
    period creates a brand new grid.

    Identified by a time-ordered UUID (v7): grids have effective dates and
    benefit from chronological sortability at the storage level.
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
    """An emitted quote — immutable, references the grid used at computation time.

    Identified by a time-ordered UUID (v7): quotes are inherently timestamped
    events and querying them by time range is a common access pattern.
    """

    id: UUID
    grid_id: UUID
    zone: str
    mode: Mode
    duration_min: int
    amount_eur: Decimal
    breakdown: dict
    computed_at: datetime
