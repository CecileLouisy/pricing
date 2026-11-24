"""Access log — one line per HTTP request with status and duration."""

import logging
import time

from fastapi import Request, Response

logger = logging.getLogger("pricing.http")


async def request_logging_middleware(request: Request, call_next) -> Response:
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        logger.log(
            level,
            "event=http_request method=%s path=%s status=%d duration_ms=%.1f",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )
