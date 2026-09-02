"""Simple admin token check (X-Admin-Token header)."""

from fastapi import Header, HTTPException, status

from app.config import settings


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Reject any request that does not carry a valid X-Admin-Token header."""
    expected = settings.ADMIN_TOKEN
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid X-Admin-Token"},
        )
