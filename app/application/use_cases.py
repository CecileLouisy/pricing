"""Use cases — orchestration des règles du domaine et des ports.

Chaque use case est une fonction pure d'orchestration. Elle reçoit ses
dépendances (repositories) en paramètres, permettant de tester avec des
implémentations en mémoire.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.ports import GridRepository, QuoteRepository
from app.domain.errors import (
    GridNotFound,
    InvalidFreePeriod,
    InvalidRate,
    ModeNotFound,
    QuoteNotFound,
    RateAlreadyExists,
    ZoneNotFound,
)
from app.domain.models import PriceGrid, Quote, Rate
from app.domain.pricing_rules import compute_reserved, compute_walk_in
from app.domain.value_objects import Mode


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_current_grid(grids: GridRepository) -> PriceGrid:
    grid = grids.get_current()
    if grid is None:
        raise GridNotFound("No active grid")
    return grid


# ---------- Lecture ----------


def get_current_grid(grids: GridRepository) -> PriceGrid:
    return _require_current_grid(grids)


def get_grid_by_id(grid_id: UUID, grids: GridRepository) -> PriceGrid:
    grid = grids.get_by_id(grid_id)
    if grid is None:
        raise GridNotFound(str(grid_id))
    return grid


def list_grids(grids: GridRepository) -> list[PriceGrid]:
    return grids.list_all()


def get_quote(quote_id: UUID, quotes: QuoteRepository) -> Quote:
    quote = quotes.get_by_id(quote_id)
    if quote is None:
        raise QuoteNotFound(str(quote_id))
    return quote


# ---------- Calcul de prix ----------


def compute_quote(
    zone: str,
    mode: Mode,
    duration_min: int,
    grids: GridRepository,
    quotes: QuoteRepository,
) -> Quote:
    grid = _require_current_grid(grids)

    rate = grid.find_rate(zone, mode)
    if rate is None:
        # Distinguer zone inconnue vs. mode manquant pour cette zone.
        zones_available = {r.zone for r in grid.rates}
        if zone not in zones_available:
            raise ZoneNotFound(zone)
        raise ModeNotFound(f"mode '{mode.value}' not defined for zone '{zone}'")

    if mode is Mode.WALK_IN:
        amount, breakdown = compute_walk_in(
            duration_min=duration_min,
            free_period_min=grid.free_period_min,
            hourly_rate_eur=rate.hourly_rate_eur,
        )
    else:
        amount, breakdown = compute_reserved(
            duration_min=duration_min,
            hourly_rate_eur=rate.hourly_rate_eur,
        )

    breakdown = {"zone": zone, "mode": mode.value, **breakdown}

    quote = Quote(
        id=uuid4(),
        grid_id=grid.id,
        zone=zone,
        mode=mode,
        duration_min=duration_min,
        amount_eur=amount,
        breakdown=breakdown,
        computed_at=_now(),
    )
    quotes.save(quote)
    return quote


# ---------- Administration : chaque écriture crée une nouvelle grille ----------


def _validate_rate_amount(hourly_rate_eur: Decimal) -> None:
    if hourly_rate_eur <= 0:
        raise InvalidRate(f"hourly_rate_eur must be > 0, got {hourly_rate_eur}")


def _clone_rates(
    source: PriceGrid,
    new_grid_id: UUID,
    replace: dict[tuple[str, Mode], Decimal] | None = None,
    add: list[tuple[str, Mode, Decimal]] | None = None,
) -> tuple[Rate, ...]:
    replace = replace or {}
    add = add or []
    rates: list[Rate] = []
    for r in source.rates:
        new_amount = replace.get((r.zone, r.mode), r.hourly_rate_eur)
        rates.append(
            Rate(
                id=uuid4(),
                grid_id=new_grid_id,
                zone=r.zone,
                mode=r.mode,
                hourly_rate_eur=new_amount,
            )
        )
    for zone, mode, amount in add:
        rates.append(
            Rate(
                id=uuid4(),
                grid_id=new_grid_id,
                zone=zone,
                mode=mode,
                hourly_rate_eur=amount,
            )
        )
    return tuple(rates)


def _new_grid_from(
    current: PriceGrid,
    *,
    free_period_min: int | None = None,
    replace: dict[tuple[str, Mode], Decimal] | None = None,
    add: list[tuple[str, Mode, Decimal]] | None = None,
) -> PriceGrid:
    new_id = uuid4()
    now = _now()
    return PriceGrid(
        id=new_id,
        version=current.version + 1,
        free_period_min=current.free_period_min if free_period_min is None else free_period_min,
        effective_from=now,
        effective_to=None,
        created_at=now,
        rates=_clone_rates(current, new_id, replace=replace, add=add),
    )


def update_rate(
    zone: str,
    mode: Mode,
    new_hourly_rate_eur: Decimal,
    grids: GridRepository,
) -> PriceGrid:
    _validate_rate_amount(new_hourly_rate_eur)
    current = _require_current_grid(grids)
    if current.find_rate(zone, mode) is None:
        zones_available = {r.zone for r in current.rates}
        if zone not in zones_available:
            raise ZoneNotFound(zone)
        raise ModeNotFound(f"mode '{mode.value}' not defined for zone '{zone}'")
    new_grid = _new_grid_from(current, replace={(zone, mode): new_hourly_rate_eur})
    return grids.publish(new_grid)


def create_rate(
    zone: str,
    mode: Mode,
    hourly_rate_eur: Decimal,
    grids: GridRepository,
) -> PriceGrid:
    _validate_rate_amount(hourly_rate_eur)
    current = _require_current_grid(grids)
    if current.find_rate(zone, mode) is not None:
        raise RateAlreadyExists(f"rate already exists for ({zone}, {mode.value})")
    new_grid = _new_grid_from(current, add=[(zone, mode, hourly_rate_eur)])
    return grids.publish(new_grid)


def update_free_period(
    new_free_period_min: int,
    grids: GridRepository,
) -> PriceGrid:
    if new_free_period_min < 0:
        raise InvalidFreePeriod(f"free_period_min must be >= 0, got {new_free_period_min}")
    current = _require_current_grid(grids)
    new_grid = _new_grid_from(current, free_period_min=new_free_period_min)
    return grids.publish(new_grid)
