"""Grid lookup endpoints (current and historical)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_session
from app.adapters.api.schemas import GridResponse, GridSummaryResponse
from app.adapters.db.grid_repository import SqlGridRepository
from app.application import use_cases

router = APIRouter(tags=["grids"])


@router.get("/grids", response_model=list[GridSummaryResponse], summary="List all grids")
def list_grids(session: Session = Depends(get_session)) -> list[GridSummaryResponse]:
    grids = use_cases.list_grids(SqlGridRepository(session))
    return [GridSummaryResponse.from_domain(g) for g in grids]


@router.get("/grids/current", response_model=GridResponse, summary="Active grid")
def get_current(session: Session = Depends(get_session)) -> GridResponse:
    grid = use_cases.get_current_grid(SqlGridRepository(session))
    return GridResponse.from_domain(grid)


@router.get("/grids/{grid_id}", response_model=GridResponse, summary="Historical grid")
def get_by_id(grid_id: UUID, session: Session = Depends(get_session)) -> GridResponse:
    grid = use_cases.get_grid_by_id(grid_id, SqlGridRepository(session))
    return GridResponse.from_domain(grid)
