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
