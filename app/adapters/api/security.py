"""Security utilities — admin and API key authentication, headers, rate limiting."""

import hmac
import logging

from fastapi import Header, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import metrics
from app.config import settings

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger("pricing.security")


def _matches(received: str, expected: str) -> bool:
    """Constant-time comparison; bytes so that a non-ASCII header cannot raise an error."""
    return bool(expected) and hmac.compare_digest(received.encode(), expected.encode())


def _unauthorized(header: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": f"Missing or invalid {header}"},
    )


def require_admin(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    """Reject any request that does not carry a valid X-Admin-Token header."""
    if not x_admin_token or not _matches(x_admin_token, settings.ADMIN_TOKEN):
        reason = "missing_token" if not x_admin_token else "invalid_token"
        logger.warning(
            "event=admin_auth_failed reason=%s method=%s path=%s",
            reason,
            request.method,
            request.url.path,
        )
        metrics.record_admin_auth_failure(reason)
        raise _unauthorized("X-Admin-Token")
    request.state.caller = "admin"


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> str:
    """Identify the calling service (Booking, Access) from its X-API-Key header.

    Each service has its own key: logs and metrics show who called, and one key
    can be revoked without affecting the other service.
    """
    caller = None
    if x_api_key:
        for name, expected in settings.api_keys.items():
            if _matches(x_api_key, expected):
                caller = name
    if caller is None:
        # The received key is never logged.
        reason = "missing_key" if not x_api_key else "invalid_key"
        logger.warning(
            "event=api_auth_failed reason=%s method=%s path=%s",
            reason,
            request.method,
            request.url.path,
        )
        metrics.record_api_auth_failure(reason)
        raise _unauthorized("X-API-Key")
    request.state.caller = caller
    metrics.record_api_call(caller)
    return caller


def require_api_key_or_admin(
    request: Request,
    x_api_key: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> str:
    """Calling services use their API key; the admin console uses the admin token."""
    if x_admin_token and _matches(x_admin_token, settings.ADMIN_TOKEN):
        request.state.caller = "admin"
        return "admin"
    return require_api_key(request, x_api_key)


async def security_headers_middleware(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response
