"""Outbound interfaces (ports) implemented by adapters/db.

Uses `typing.Protocol` to avoid forcing inheritance: any implementation that
exposes these methods satisfies the contract.
"""

from typing import Protocol
from uuid import UUID

from app.domain.models import PriceGrid, Quote


class GridRepository(Protocol):
    def get_current(self) -> PriceGrid | None: ...

    def get_by_id(self, grid_id: UUID) -> PriceGrid | None: ...

    def list_all(self) -> list[PriceGrid]: ...

    def publish(self, new_grid: PriceGrid) -> PriceGrid:
        """Close the currently active grid (effective_to = now) and persist the new one."""
        ...


class QuoteRepository(Protocol):
    def save(self, quote: Quote) -> None: ...

    def get_by_id(self, quote_id: UUID) -> Quote | None: ...
