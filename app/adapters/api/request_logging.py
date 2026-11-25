"""Access log and HTTP metrics — one line and one measure per request."""

import logging
import time

from fastapi import Request, Response

from app import metrics

logger = logging.getLogger("pricing.http")

# Scraped every few seconds by Prometheus: logged at DEBUG to keep the logs readable.
_QUIET_PATHS = {"/metrics"}


def _route_template(request: Request) -> str:
    """Route template ("/quotes/{quote_id}"), never the raw path.

    Raw paths would create one metric series per quote ID or per unknown URL
    probed by a scanner.
    """
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


async def request_logging_middleware(request: Request, call_next) -> Response:
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_s = time.perf_counter() - start
        metrics.record_http_request(
            request.method, _route_template(request), status_code, duration_s
        )
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        elif request.url.path in _QUIET_PATHS:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logger.log(
            level,
            "event=http_request method=%s path=%s status=%d duration_ms=%.1f",
            request.method,
            request.url.path,
            status_code,
            duration_s * 1000,
        )
