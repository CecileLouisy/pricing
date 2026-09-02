"""Configuration SQLAlchemy et amorçage de la base."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

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
    """Crée les tables si absentes et amorce une grille initiale si base vide."""
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        existing = session.execute(select(GridORM).limit(1)).first()
        if existing is None:
            _seed_initial_grid(session)
            session.commit()


def _seed_initial_grid(session: Session) -> None:
    """Grille v1 : 5 zones × 2 modes, gratuité initiale de 15 min.

    Les montants sont volontairement simples et modifiables ensuite par l'admin.
    """
    now = datetime.now(timezone.utc)
    grid_id = str(uuid4())
    grid = GridORM(
        id=grid_id,
        version=1,
        free_period_min=15,
        effective_from=now,
        effective_to=None,
        created_at=now,
    )
    session.add(grid)

    # Tarifs par défaut (EUR / heure). L'admin ajustera via PATCH ensuite.
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
