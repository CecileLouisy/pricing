"""Database URL normalization for SQLAlchemy."""

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.neon.tech/neondb?sslmode=require",
        ),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./pricing.db", "sqlite:///./pricing.db"),
    ],
)
def test_database_url_uses_psycopg3_driver(raw, expected):
    assert Settings(DATABASE_URL=raw).sqlalchemy_database_url == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", "unknown"),
        ("21bbd5f0c2a4e5d6b7f8091a2b3c4d5e6f708192", "21bbd5f"),
    ],
)
def test_git_commit_is_shortened(raw, expected):
    assert Settings(RENDER_GIT_COMMIT=raw).git_commit == expected


SAFE = "x" * 32


def test_safe_secrets_are_accepted():
    s = Settings(ADMIN_TOKEN=SAFE, BOOKING_API_KEY=SAFE, ACCESS_API_KEY=SAFE)
    assert s.unsafe_secrets() == []


def test_default_missing_or_short_secrets_are_reported():
    s = Settings(ADMIN_TOKEN="change-me-in-production", BOOKING_API_KEY="", ACCESS_API_KEY="short")
    assert s.unsafe_secrets() == ["ADMIN_TOKEN", "BOOKING_API_KEY", "ACCESS_API_KEY"]


def test_only_configured_api_keys_are_usable():
    s = Settings(BOOKING_API_KEY=SAFE, ACCESS_API_KEY="")
    assert s.api_keys == {"booking": SAFE}
