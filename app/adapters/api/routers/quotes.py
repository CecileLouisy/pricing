"""Price simulation (public) and quotes (calling services, API key)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_session
from app.adapters.api.schemas import QuoteRequest, QuoteResponse, SimulationResponse
from app.adapters.api.security import limiter, require_api_key, require_api_key_or_admin
from app.adapters.db.grid_repository import SqlGridRepository
from app.adapters.db.quote_repository import SqlQuoteRepository
from app.application import use_cases
from app.correlation import get_correlation_id

router = APIRouter(tags=["quotes"])


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Simulate a price (public, nothing stored)",
)
@limiter.limit("30/minute")
def simulate(
    request: Request,
    body: QuoteRequest,
    session: Session = Depends(get_session),
) -> SimulationResponse:
    amount, breakdown, grid = use_cases.simulate_price(
        zone=body.zone,
        mode=body.mode,
        duration_min=body.duration_min,
        grids=SqlGridRepository(session),
    )
    return SimulationResponse(
        grid_id=grid.id,
        grid_version=grid.version,
        amount_eur=amount,
        breakdown=breakdown,
    )


@router.post(
    "/quote",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
    summary="Compute and persist a quote (Booking, Access: X-API-Key)",
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
        correlation_id=get_correlation_id(),
    )
    grid = grids.get_by_id(quote.grid_id)
    return QuoteResponse.from_domain(quote, grid_version=grid.version if grid else None)


@router.get(
    "/quotes/{quote_id}",
    response_model=QuoteResponse,
    dependencies=[Depends(require_api_key_or_admin)],
    summary="Retrieve a past quote (X-API-Key or X-Admin-Token)",
)
def get_quote(quote_id: UUID, session: Session = Depends(get_session)) -> QuoteResponse:
    quotes = SqlQuoteRepository(session)
    grids = SqlGridRepository(session)
    quote = use_cases.get_quote(quote_id, quotes)
    grid = grids.get_by_id(quote.grid_id)
    return QuoteResponse.from_domain(quote, grid_version=grid.version if grid else None)
