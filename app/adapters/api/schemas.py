"""Pydantic DTOs for the HTTP layer (input validation + output serialization)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import PriceGrid, Quote, Rate
from app.domain.value_objects import MAX_DURATION_MIN, Mode


# --------- Requests ---------


class QuoteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    zone: str = Field(..., min_length=1, max_length=50, examples=["standard"])
    mode: Mode = Field(..., examples=["walk_in"])
    duration_min: int = Field(..., gt=0, le=MAX_DURATION_MIN, examples=[75])


class RateUpdateRequest(BaseModel):
    hourly_rate_eur: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2, examples=["3.50"])


class RateCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    zone: str = Field(..., min_length=1, max_length=50, examples=["premium"])
    mode: Mode = Field(..., examples=["walk_in"])
    hourly_rate_eur: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2, examples=["5.00"])


class FreePeriodUpdateRequest(BaseModel):
    free_period_min: int = Field(..., ge=0, le=180, examples=[15])


# --------- Responses ---------


class RateResponse(BaseModel):
    id: UUID
    zone: str
    mode: Mode
    hourly_rate_eur: Decimal

    @classmethod
    def from_domain(cls, rate: Rate) -> "RateResponse":
        return cls(
            id=rate.id,
            zone=rate.zone,
            mode=rate.mode,
            hourly_rate_eur=rate.hourly_rate_eur,
        )


class GridResponse(BaseModel):
    id: UUID
    version: int
    free_period_min: int
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    rates: list[RateResponse]

    @classmethod
    def from_domain(cls, grid: PriceGrid) -> "GridResponse":
        return cls(
            id=grid.id,
            version=grid.version,
            free_period_min=grid.free_period_min,
            effective_from=grid.effective_from,
            effective_to=grid.effective_to,
            created_at=grid.created_at,
            rates=[RateResponse.from_domain(r) for r in grid.rates],
        )


class GridSummaryResponse(BaseModel):
    id: UUID
    version: int
    effective_from: datetime
    effective_to: datetime | None

    @classmethod
    def from_domain(cls, grid: PriceGrid) -> "GridSummaryResponse":
        return cls(
            id=grid.id,
            version=grid.version,
            effective_from=grid.effective_from,
            effective_to=grid.effective_to,
        )


class QuoteResponse(BaseModel):
    quote_id: UUID
    grid_id: UUID
    grid_version: int | None = None
    amount_eur: Decimal
    currency: str = "EUR"
    breakdown: dict
    computed_at: datetime

    @classmethod
    def from_domain(cls, quote: Quote, grid_version: int | None = None) -> "QuoteResponse":
        return cls(
            quote_id=quote.id,
            grid_id=quote.grid_id,
            grid_version=grid_version,
            amount_eur=quote.amount_eur,
            breakdown=quote.breakdown,
            computed_at=quote.computed_at,
        )


class FreePeriodResponse(BaseModel):
    free_period_min: int
    grid_id: UUID
    grid_version: int


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "pricing"


class ErrorResponse(BaseModel):
    code: str
    message: str
