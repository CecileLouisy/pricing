"""Map domain errors to structured HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        status_code = _HTTP_STATUS_BY_ERROR.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content={"code": exc.code, "message": str(exc)},
        )
