"""Use case tests with in-memory repositories (no DB, no HTTP)."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from uuid6 import uuid7

from app.application import use_cases
from app.domain.errors import (
    GridNotFound,
    InvalidRate,
    QuoteNotFound,
    RateAlreadyExists,
    ZoneNotFound,
)
from app.domain.models import PriceGrid, Quote, Rate
from app.domain.value_objects import Mode


# --------- Fake repositories ---------


class InMemoryGridRepo:
    def __init__(self, initial: PriceGrid | None = None):
        self._grids: dict[UUID, PriceGrid] = {}
        if initial:
            self._grids[initial.id] = initial

    def get_current(self):
        return next(
            (g for g in self._grids.values() if g.effective_to is None),
            None,
        )

    def get_by_id(self, grid_id):
        return self._grids.get(grid_id)

    def list_all(self):
        return sorted(self._grids.values(), key=lambda g: g.version, reverse=True)

    def publish(self, new_grid):
        # Close the active grid by replacing it with an immutable closed version.
        current = self.get_current()
        if current:
            closed = PriceGrid(
                id=current.id,
                version=current.version,
                free_period_min=current.free_period_min,
                effective_from=current.effective_from,
                effective_to=datetime.now(timezone.utc),
                created_at=current.created_at,
                rates=current.rates,
            )
            self._grids[current.id] = closed
        self._grids[new_grid.id] = new_grid
        return new_grid


class InMemoryQuoteRepo:
    def __init__(self):
        self._quotes: dict[UUID, Quote] = {}

    def save(self, quote):
        self._quotes[quote.id] = quote

    def get_by_id(self, quote_id):
        return self._quotes.get(quote_id)


# --------- Fixtures ---------


def _make_grid() -> PriceGrid:
    now = datetime.now(timezone.utc)
    grid_id = uuid7()
    rates = (
        Rate(uuid4(), grid_id, "standard", Mode.WALK_IN, Decimal("3.00")),
        Rate(uuid4(), grid_id, "standard", Mode.RESERVED, Decimal("2.50")),
        Rate(uuid4(), grid_id, "xl", Mode.WALK_IN, Decimal("4.50")),
    )
    return PriceGrid(
        id=grid_id,
        version=1,
        free_period_min=15,
        effective_from=now,
        effective_to=None,
        created_at=now,
        rates=rates,
    )


@pytest.fixture
def grids():
    return InMemoryGridRepo(_make_grid())


@pytest.fixture
def quotes():
    return InMemoryQuoteRepo()


# --------- Compute ---------


class TestComputeQuote:
    def test_walk_in_computes_and_persists(self, grids, quotes):
        quote = use_cases.compute_quote("standard", Mode.WALK_IN, 75, grids, quotes)
        assert quote.amount_eur == Decimal("3.00")
        assert quotes.get_by_id(quote.id) is not None
        assert quote.grid_id == grids.get_current().id

    def test_reserved_computes_correctly(self, grids, quotes):
        quote = use_cases.compute_quote("standard", Mode.RESERVED, 120, grids, quotes)
        assert quote.amount_eur == Decimal("5.00")  # 2h x 2.50

    def test_unknown_zone_raises(self, grids, quotes):
        with pytest.raises(ZoneNotFound):
            use_cases.compute_quote("moon_base", Mode.WALK_IN, 60, grids, quotes)

    def test_no_active_grid_raises(self, quotes):
        empty = InMemoryGridRepo()
        with pytest.raises(GridNotFound):
            use_cases.compute_quote("standard", Mode.WALK_IN, 60, empty, quotes)


# --------- Retrieval ---------


class TestGetQuote:
    def test_returns_stored_quote(self, grids, quotes):
        created = use_cases.compute_quote("standard", Mode.WALK_IN, 60, grids, quotes)
        retrieved = use_cases.get_quote(created.id, quotes)
        assert retrieved == created

    def test_missing_raises(self, quotes):
        with pytest.raises(QuoteNotFound):
            use_cases.get_quote(uuid7(), quotes)


# --------- Admin — versioning ---------


class TestUpdateRate:
    def test_creates_new_grid_version(self, grids):
        v1 = grids.get_current()
        new_grid = use_cases.update_rate("standard", Mode.WALK_IN, Decimal("5.00"), grids)
        assert new_grid.version == v1.version + 1
        assert new_grid.find_rate("standard", Mode.WALK_IN).hourly_rate_eur == Decimal("5.00")
        # v1 is now closed
        assert grids.get_by_id(v1.id).effective_to is not None

    def test_old_quotes_still_reference_old_grid(self, grids, quotes):
        quote_before = use_cases.compute_quote("standard", Mode.WALK_IN, 60, grids, quotes)
        use_cases.update_rate("standard", Mode.WALK_IN, Decimal("10.00"), grids)
        assert quotes.get_by_id(quote_before.id).amount_eur == Decimal("2.25")  # original rate

    def test_rejects_negative_rate(self, grids):
        with pytest.raises(InvalidRate):
            use_cases.update_rate("standard", Mode.WALK_IN, Decimal("-1"), grids)


class TestCreateRate:
    def test_adds_rate_and_creates_new_grid(self, grids):
        v1 = grids.get_current()
        new_grid = use_cases.create_rate("xl", Mode.RESERVED, Decimal("4.00"), grids)
        assert new_grid.version == v1.version + 1
        assert new_grid.find_rate("xl", Mode.RESERVED).hourly_rate_eur == Decimal("4.00")

    def test_rejects_duplicate(self, grids):
        with pytest.raises(RateAlreadyExists):
            use_cases.create_rate("standard", Mode.WALK_IN, Decimal("5.00"), grids)


class TestUpdateFreePeriod:
    def test_updates_and_creates_new_grid(self, grids):
        v1 = grids.get_current()
        new_grid = use_cases.update_free_period(30, grids)
        assert new_grid.free_period_min == 30
        assert new_grid.version == v1.version + 1
