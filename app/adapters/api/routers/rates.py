"""Endpoints de consultation et modification des tarifs.

Lectures publiques (grille active). Écritures protégées par X-Admin-Token.
Chaque écriture crée automatiquement une nouvelle version de grille.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_session
from app.adapters.api.schemas import (
    GridResponse,
    RateCreateRequest,
    RateResponse,
    RateUpdateRequest,
)
from app.adapters.api.security import require_admin
from app.adapters.db.grid_repository import SqlGridRepository
from app.application import use_cases
from app.domain.errors import ZoneNotFound
from app.domain.value_objects import Mode

router = APIRouter(tags=["rates"])


@router.get("/rates", response_model=list[RateResponse], summary="Tarifs de la grille active")
def list_rates(session: Session = Depends(get_session)) -> list[RateResponse]:
    grid = use_cases.get_current_grid(SqlGridRepository(session))
    return [RateResponse.from_domain(r) for r in grid.rates]


@router.get(
    "/rates/{zone}",
    response_model=list[RateResponse],
    summary="Tarifs (reserved et walk_in) d'une zone",
)
def get_rates_for_zone(zone: str, session: Session = Depends(get_session)) -> list[RateResponse]:
    grid = use_cases.get_current_grid(SqlGridRepository(session))
    rates = [r for r in grid.rates if r.zone == zone]
    if not rates:
        raise ZoneNotFound(zone)
    return [RateResponse.from_domain(r) for r in rates]


@router.post(
    "/rates",
    response_model=GridResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Créer un nouveau tarif (admin)",
)
def create_rate(
    body: RateCreateRequest,
    session: Session = Depends(get_session),
) -> GridResponse:
    grids = SqlGridRepository(session)
    new_grid = use_cases.create_rate(body.zone, body.mode, body.hourly_rate_eur, grids)
    return GridResponse.from_domain(new_grid)


@router.patch(
    "/rates/{zone}/{mode}",
    response_model=GridResponse,
    dependencies=[Depends(require_admin)],
    summary="Modifier un tarif (admin)",
)
def update_rate(
    zone: str,
    mode: Mode,
    body: RateUpdateRequest,
    session: Session = Depends(get_session),
) -> GridResponse:
    grids = SqlGridRepository(session)
    new_grid = use_cases.update_rate(zone, mode, body.hourly_rate_eur, grids)
    return GridResponse.from_domain(new_grid)
