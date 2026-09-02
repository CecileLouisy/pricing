"""FastAPI entry point — application assembly."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.api.error_handlers import register_error_handlers
from app.adapters.api.routers import grids, health, quotes, rates, settings as settings_router
from app.adapters.db.engine import init_db
from app.config import settings

API_DESCRIPTION = """
Pricing service of the Parking Management project.

**Role**: compute the price of a parking session or a reservation from a
versioned price grid, guaranteeing traceability of the grid used for every
computation.

- Public reads (active grid, history)
- Admin-only writes (`X-Admin-Token` header)
- Every change publishes a new grid version
- Every computed quote is persisted and linked to its grid
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
