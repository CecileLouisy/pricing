"""SQLAlchemy implementation of the QuoteRepository port."""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.db.orm_models import QuoteORM
from app.domain.models import Quote
from app.domain.value_objects import Mode


def _to_domain(row: QuoteORM) -> Quote:
    return Quote(
        id=UUID(row.id),
        grid_id=UUID(row.grid_id),
        zone=row.zone,
        mode=Mode(row.mode),
        duration_min=row.duration_min,
        amount_eur=row.amount_eur,
        breakdown=json.loads(row.breakdown_json),
        computed_at=row.computed_at,
    )


class SqlQuoteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, quote: Quote) -> None:
        self._session.add(
            QuoteORM(
                id=str(quote.id),
                grid_id=str(quote.grid_id),
                zone=quote.zone,
                mode=quote.mode.value,
                duration_min=quote.duration_min,
                amount_eur=quote.amount_eur,
                breakdown_json=json.dumps(quote.breakdown),
                computed_at=quote.computed_at,
            )
        )
        self._session.commit()

    def get_by_id(self, quote_id: UUID) -> Quote | None:
        row = self._session.get(QuoteORM, str(quote_id))
        return _to_domain(row) if row else None
