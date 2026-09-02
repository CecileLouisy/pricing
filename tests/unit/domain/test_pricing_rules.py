"""Unit tests for the pricing rules — pure domain logic, no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.domain.errors import InvalidDuration
from app.domain.pricing_rules import compute_reserved, compute_walk_in


class TestComputeWalkIn:
    def test_typical_case_75_minutes(self):
        # 75 min - 15 free = 60 billable = 4 quarters x 0.75 EUR = 3.00 EUR
        amount, breakdown = compute_walk_in(75, free_period_min=15, hourly_rate_eur=Decimal("3.00"))
        assert amount == Decimal("3.00")
        assert breakdown["billable_min"] == 60
        assert breakdown["quarters"] == 4

    def test_under_free_period_returns_zero(self):
        amount, _ = compute_walk_in(10, free_period_min=15, hourly_rate_eur=Decimal("3.00"))
        assert amount == Decimal("0.00")

    def test_exactly_free_period_returns_zero(self):
        amount, _ = compute_walk_in(15, free_period_min=15, hourly_rate_eur=Decimal("3.00"))
        assert amount == Decimal("0.00")

    def test_started_quarter_is_due(self):
        # 16 min - 15 free = 1 billable min -> 1 full quarter due = 0.75 EUR
        amount, breakdown = compute_walk_in(16, free_period_min=15, hourly_rate_eur=Decimal("3.00"))
        assert amount == Decimal("0.75")
        assert breakdown["quarters"] == 1

    def test_zero_free_period(self):
        amount, _ = compute_walk_in(60, free_period_min=0, hourly_rate_eur=Decimal("3.00"))
        assert amount == Decimal("3.00")

    def test_invalid_duration_zero(self):
        with pytest.raises(InvalidDuration):
            compute_walk_in(0, free_period_min=15, hourly_rate_eur=Decimal("3.00"))

    def test_invalid_duration_negative(self):
        with pytest.raises(InvalidDuration):
            compute_walk_in(-1, free_period_min=15, hourly_rate_eur=Decimal("3.00"))

    def test_invalid_duration_over_max(self):
        with pytest.raises(InvalidDuration):
            compute_walk_in(10_081, free_period_min=15, hourly_rate_eur=Decimal("3.00"))


class TestComputeReserved:
    def test_typical_case_3_hours(self):
        amount, breakdown = compute_reserved(180, hourly_rate_eur=Decimal("4.00"))
        assert amount == Decimal("12.00")
        assert breakdown["hours"] == 3

    def test_one_hour(self):
        amount, _ = compute_reserved(60, hourly_rate_eur=Decimal("2.50"))
        assert amount == Decimal("2.50")

    def test_max_duration_7_days(self):
        amount, breakdown = compute_reserved(10_080, hourly_rate_eur=Decimal("1.00"))
        assert amount == Decimal("168.00")
        assert breakdown["hours"] == 168

    def test_rejects_non_hourly_duration(self):
        with pytest.raises(InvalidDuration):
            compute_reserved(75, hourly_rate_eur=Decimal("3.00"))

    def test_rejects_over_max(self):
        with pytest.raises(InvalidDuration):
            compute_reserved(10_140, hourly_rate_eur=Decimal("1.00"))
