"""Correlation ID validation: opaque, safe to write in key=value logs."""

import pytest

from app.correlation import is_valid, new_correlation_id


@pytest.mark.parametrize(
    "value",
    ["3f2a9c1e-7b4d-4c1a-9e2f-0a1b2c3d4e5f", "booking-42", "ACCESS_7", "a" * 128],
)
def test_accepts_opaque_ids(value):
    assert is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["", "a" * 129, "with space", "line\nbreak", "key=value", "accent-é"],
)
def test_rejects_unsafe_ids(value):
    assert not is_valid(value)


def test_generated_id_is_valid():
    assert is_valid(new_correlation_id())
