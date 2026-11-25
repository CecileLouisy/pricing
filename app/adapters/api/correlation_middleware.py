"""Correlation ID middleware — reuse the caller's X-Correlation-ID or generate one."""

import logging

from fastapi import Request, Response

from app.correlation import (
    HEADER,
    is_valid,
    new_correlation_id,
    set_correlation_id,
)

logger = logging.getLogger("pricing.http")


async def correlation_id_middleware(request: Request, call_next) -> Response:
    received = request.headers.get(HEADER)
    if received is not None and is_valid(received):
        correlation_id = received
    else:
        correlation_id = new_correlation_id()

    # Not reset after the request: each request runs in its own task context, and the
    # error handler for unexpected exceptions runs outside this middleware but must
    # still log the ID.
    set_correlation_id(correlation_id)

    if received is not None and correlation_id != received:
        # The invalid value itself is not logged: it may contain line breaks.
        logger.warning(
            "event=invalid_correlation_id length=%d action=replaced",
            len(received),
        )

    response = await call_next(request)
    response.headers[HEADER] = correlation_id
    return response
