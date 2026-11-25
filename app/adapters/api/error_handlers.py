"""Map domain errors to structured HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import metrics
from app.domain.errors import (
    DomainError,
    GridNotFound,
    InvalidDuration,
    InvalidFreePeriod,
    InvalidMode,
    InvalidRate,
    ModeNotFound,
    QuoteNotFound,
    RateAlreadyExists,
    Unauthorized,
    ZoneNotFound,
)

_HTTP_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    ZoneNotFound: 404,
    ModeNotFound: 404,
    QuoteNotFound: 404,
    GridNotFound: 404,
    InvalidDuration: 400,
    InvalidMode: 400,
    InvalidRate: 400,
    InvalidFreePeriod: 400,
    RateAlreadyExists: 409,
    Unauthorized: 401,
}

logger = logging.getLogger("pricing.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = _HTTP_STATUS_BY_ERROR.get(type(exc), 500)
        logger.warning(
            "event=domain_error code=%s path=%s detail=%r",
            exc.code,
            request.url.path,
            str(exc),
        )
        metrics.record_domain_error(exc.code)
        return JSONResponse(
            status_code=status_code,
            content={"code": exc.code, "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full traceback goes to the logs only; the client gets a generic message.
        logger.exception("event=unexpected_error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )
