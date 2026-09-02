"""Endpoint de disponibilité pour le monitoring Render."""

from fastapi import APIRouter

from app.adapters.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Statut du service")
def health() -> HealthResponse:
    return HealthResponse()
