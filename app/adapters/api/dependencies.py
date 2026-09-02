"""FastAPI dependencies — provides a per-request DB session."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.adapters.db.engine import SessionLocal


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
