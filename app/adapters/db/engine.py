"""SQLAlchemy setup and database bootstrap."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker
from uuid6 import uuid7

from app.adapters.db.orm_models import Base, GridORM, RateORM
from app.config import settings
from app.domain.value_objects import INITIAL_ZONES, Mode

logger = logging.getLogger("pricing.db")

_IS_SQLITE = settings.sqlalchemy_database_url.startswith("sqlite")

engine = create_engine(
    settings.sqlalchemy_database_url,
    echo=False,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
    # Neon suspends idle databases and closes their connections: test each pooled
    # connection before use and recycle it before the server-side timeout.
    pool_pre_ping=not _IS_SQLITE,
    pool_recycle=300,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# Columns added after the first deployment: (table, column, SQL type).
# create_all() creates missing tables but never alters an existing one, so these
# columns are added to databases created before them (e.g. the Neon database).
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (("quote", "correlation_id", "VARCHAR(128)"),)


def init_db() -> None:
    """Create tables if missing, add new columns, seed an initial grid if empty."""
    Base.metadata.create_all(engine)
    _add_missing_columns()
    with SessionLocal() as session:
        existing = session.execute(select(GridORM).limit(1)).first()
        if existing is None:
            _seed_initial_grid(session)
            session.commit()


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    for table, column, sql_type in _ADDED_COLUMNS:
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            continue
        with engine.begin() as conn:
            # Names and type come from the constant above, never from user input.
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
        logger.info("event=schema_upgraded table=%s column=%s", table, column)


def _seed_initial_grid(session: Session) -> None:
    """Grid v1: 5 zones x 2 modes, initial free period of 60 minutes.

    Amounts are intentionally simple and can be updated by an admin later.
    Grid identifier uses UUIDv7 (time-ordered); rate identifiers use UUIDv4.
    """
    now = datetime.now(UTC)
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
        "standard": (Decimal("3.00"), Decimal("2.50")),
        "xl": (Decimal("4.50"), Decimal("4.00")),
        "handicapped": (Decimal("1.50"), Decimal("1.25")),
        "electric": (Decimal("3.50"), Decimal("3.00")),
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
