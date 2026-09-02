"""Health check endpoint for Render monitoring."""

from fastapi import APIRouter

from app.adapters.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service status")
def health() -> HealthResponse:
    return HealthResponse()
