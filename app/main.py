"""Point d'entrée FastAPI — assemblage de l'application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.api.error_handlers import register_error_handlers
from app.adapters.api.routers import grids, health, quotes, rates, settings as settings_router
from app.adapters.db.engine import init_db
from app.config import settings

API_DESCRIPTION = """
Service de tarification du projet Parking Management.

**Rôle** : calculer le prix d'un stationnement ou d'une réservation à partir
d'une grille tarifaire versionnée, en garantissant la traçabilité de la grille
utilisée pour chaque calcul.

- Lectures publiques (grille active, historique)
- Écritures réservées à l'admin (header `X-Admin-Token`)
- Chaque modification crée une nouvelle version de grille
- Chaque devis calculé est persisté et lié à sa grille
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Pricing — Parking Management",
    version="1.0.0",
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
    allow_credentials=False,
)

register_error_handlers(app)

app.include_router(health.router)
app.include_router(quotes.router)
app.include_router(rates.router)
app.include_router(grids.router)
app.include_router(settings_router.router)
