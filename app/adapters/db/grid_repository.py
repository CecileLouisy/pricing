"""SQLAlchemy implementation of the GridRepository port."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.db.orm_models import GridORM, RateORM
from app.domain.models import PriceGrid, Rate
from app.domain.value_objects import Mode


def _to_domain(row: GridORM) -> PriceGrid:
    return PriceGrid(
        id=UUID(row.id),
        version=row.version,
        free_period_min=row.free_period_min,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        created_at=row.created_at,
        rates=tuple(
            Rate(
                id=UUID(r.id),
                grid_id=UUID(r.grid_id),
                zone=r.zone,
                mode=Mode(r.mode),
                hourly_rate_eur=r.hourly_rate_eur,
            )
            for r in row.rates
        ),
    )


class SqlGridRepository:
    """SQLAlchemy adapter — satisfies the GridRepository protocol."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(self) -> PriceGrid | None:
        stmt = select(GridORM).where(GridORM.effective_to.is_(None))
        row = self._session.execute(stmt).scalar_one_or_none()
        return _to_domain(row) if row else None

    def get_by_id(self, grid_id: UUID) -> PriceGrid | None:
        row = self._session.get(GridORM, str(grid_id))
        return _to_domain(row) if row else None

    def list_all(self) -> list[PriceGrid]:
        stmt = select(GridORM).order_by(GridORM.version.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [_to_domain(r) for r in rows]

    def publish(self, new_grid: PriceGrid) -> PriceGrid:
        # 1. Close the currently active grid (if any).
        current_stmt = select(GridORM).where(GridORM.effective_to.is_(None))
        current = self._session.execute(current_stmt).scalar_one_or_none()
        if current is not None:
            current.effective_to = datetime.now(timezone.utc)

        # 2. Insert the new grid and its rates.
        new_row = GridORM(
            id=str(new_grid.id),
            version=new_grid.version,
            free_period_min=new_grid.free_period_min,
            effective_from=new_grid.effective_from,
            effective_to=None,
            created_at=new_grid.created_at,
        )
        self._session.add(new_row)
        for r in new_grid.rates:
            self._session.add(
                RateORM(
                    id=str(r.id),
                    grid_id=str(new_grid.id),
                    zone=r.zone,
                    mode=r.mode.value,
                    hourly_rate_eur=r.hourly_rate_eur,
                )
            )
        self._session.commit()
        return new_grid
