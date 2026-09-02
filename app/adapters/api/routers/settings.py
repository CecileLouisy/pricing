"""Endpoint de consultation/modification de la période de gratuité initiale."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_session
from app.adapters.api.schemas import FreePeriodResponse, FreePeriodUpdateRequest
from app.adapters.api.security import require_admin
from app.adapters.db.grid_repository import SqlGridRepository
from app.application import use_cases

router = APIRouter(tags=["settings"])


@router.get(
    "/settings/free-period",
    response_model=FreePeriodResponse,
    summary="Durée de gratuité initiale active",
)
def get_free_period(session: Session = Depends(get_session)) -> FreePeriodResponse:
    grid = use_cases.get_current_grid(SqlGridRepository(session))
    return FreePeriodResponse(
        free_period_min=grid.free_period_min,
        grid_id=grid.id,
        grid_version=grid.version,
    )


@router.patch(
    "/settings/free-period",
    response_model=FreePeriodResponse,
    dependencies=[Depends(require_admin)],
    summary="Modifier la gratuité initiale (admin)",
)
def update_free_period(
    body: FreePeriodUpdateRequest,
    session: Session = Depends(get_session),
) -> FreePeriodResponse:
    grids = SqlGridRepository(session)
    new_grid = use_cases.update_free_period(body.free_period_min, grids)
    return FreePeriodResponse(
        free_period_min=new_grid.free_period_min,
        grid_id=new_grid.id,
        grid_version=new_grid.version,
    )
