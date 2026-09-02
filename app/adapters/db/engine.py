"""SQLAlchemy setup and database bootstrap."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from uuid6 import uuid7

from app.adapters.db.orm_models import Base, GridORM, RateORM
from app.config import settings
from app.domain.value_objects import INITIAL_ZONES, Mode

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if missing and seed an initial grid if the database is empty."""
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        existing = session.execute(select(GridORM).limit(1)).first()
        if existing is None:
            _seed_initial_grid(session)
            session.commit()


def _seed_initial_grid(session: Session) -> None:
    """Grid v1: 5 zones x 2 modes, initial free period of 60 minutes.

    Amounts are intentionally simple and can be updated by an admin later.
    Grid identifier uses UUIDv7 (time-ordered); rate identifiers use UUIDv4.
    """
    now = datetime.now(timezone.utc)
    grid_id = str(uuid7())
    grid = GridORM(
        id=grid_id,
        version=1,
        free_period_min=60,
        effective_from=now,
        effective_to=None,
        created_at=now,
    )
    session.add(grid)

    # Default rates in EUR / hour. Admin can adjust via PATCH afterwards.
    defaults: dict[str, tuple[Decimal, Decimal]] = {
        # zone       : (walk_in, reserved)
        "standard":   (Decimal("3.00"), Decimal("2.50")),
        "xl":         (Decimal("4.50"), Decimal("4.00")),
        "disabled":   (Decimal("1.50"), Decimal("1.25")),
        "electric":   (Decimal("3.50"), Decimal("3.00")),
        "two_wheels": (Decimal("1.00"), Decimal("0.80")),
    }
    for zone in INITIAL_ZONES:
        walk_in_rate, reserved_rate = defaults[zone]
        session.add(
            RateORM(
                id=str(uuid4()),
                grid_id=grid_id,
                zone=zone,
                mode=Mode.WALK_IN.value,
                hourly_rate_eur=walk_in_rate,
            )
        )
        session.add(
            RateORM(
                id=str(uuid4()),
                grid_id=grid_id,
                zone=zone,
                mode=Mode.RESERVED.value,
                hourly_rate_eur=reserved_rate,
            )
        )
