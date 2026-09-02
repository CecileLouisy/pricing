"""Endpoints de calcul et consultation des devis."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_session
from app.adapters.api.schemas import QuoteRequest, QuoteResponse
from app.adapters.db.grid_repository import SqlGridRepository
from app.adapters.db.quote_repository import SqlQuoteRepository
from app.application import use_cases

router = APIRouter(tags=["quotes"])


@router.post(
    "/quote",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculer un prix et le persister",
)
def create_quote(
    body: QuoteRequest,
    session: Session = Depends(get_session),
) -> QuoteResponse:
    grids = SqlGridRepository(session)
    quotes = SqlQuoteRepository(session)
    quote = use_cases.compute_quote(
        zone=body.zone,
        mode=body.mode,
        duration_min=body.duration_min,
        grids=grids,
        quotes=quotes,
    )
    grid = grids.get_by_id(quote.grid_id)
    return QuoteResponse.from_domain(quote, grid_version=grid.version if grid else None)


@router.get(
    "/quotes/{quote_id}",
    response_model=QuoteResponse,
    summary="Retrouver un devis passé",
)
def get_quote(quote_id: UUID, session: Session = Depends(get_session)) -> QuoteResponse:
    quotes = SqlQuoteRepository(session)
    grids = SqlGridRepository(session)
    quote = use_cases.get_quote(quote_id, quotes)
    grid = grids.get_by_id(quote.grid_id)
    return QuoteResponse.from_domain(quote, grid_version=grid.version if grid else None)
