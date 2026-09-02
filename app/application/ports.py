"""Interfaces sortantes (ports) implémentées par les adapters/db.

Utilisation de `typing.Protocol` pour ne pas forcer d'héritage : n'importe quelle
implémentation qui présente ces méthodes satisfait le contrat.
"""

from typing import Protocol
from uuid import UUID

from app.domain.models import PriceGrid, Quote


class GridRepository(Protocol):
    def get_current(self) -> PriceGrid | None: ...

    def get_by_id(self, grid_id: UUID) -> PriceGrid | None: ...

    def list_all(self) -> list[PriceGrid]: ...

    def publish(self, new_grid: PriceGrid) -> PriceGrid:
        """Ferme la grille active (effective_to = now) et enregistre la nouvelle."""
        ...


class QuoteRepository(Protocol):
    def save(self, quote: Quote) -> None: ...

    def get_by_id(self, quote_id: UUID) -> Quote | None: ...
