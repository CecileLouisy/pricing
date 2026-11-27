"""FastAPI entry point — application assembly."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import __version__, metrics
from app.adapters.api.correlation_middleware import correlation_id_middleware
from app.adapters.api.error_handlers import register_error_handlers
from app.adapters.api.request_logging import request_logging_middleware
from app.adapters.api.routers import grids, health, quotes, rates, root
from app.adapters.api.routers import metrics as metrics_router
from app.adapters.api.routers import settings as settings_router
from app.adapters.api.security import limiter, security_headers_middleware
from app.adapters.db.engine import SessionLocal, init_db
from app.adapters.db.grid_repository import SqlGridRepository
from app.application import use_cases
from app.config import settings
from app.correlation import HEADER as CORRELATION_HEADER
from app.domain.value_objects import ZONE_RENAMES
from app.logging_config import configure_logging

configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger("pricing")

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


def check_production_secrets() -> None:
    """Refuse to start in production with a missing, default or too short secret."""
    unsafe = settings.unsafe_secrets()
    if settings.ENV == "production" and unsafe:
        # Only the variable names are logged, never their values.
        logger.critical("event=startup_refused reason=unsafe_secrets secrets=%s", ",".join(unsafe))
        raise RuntimeError(f"Unsafe or missing secrets in production: {', '.join(unsafe)}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    check_production_secrets()
    init_db()
    with SessionLocal() as session:
        grids = SqlGridRepository(session)
        for old_zone, new_zone in ZONE_RENAMES.items():
            use_cases.rename_zone(old_zone, new_zone, grids)
        metrics.set_active_grid_version(use_cases.get_current_grid(grids).version)
    logger.info(
        "event=startup version=%s commit=%s env=%s", __version__, settings.git_commit, settings.ENV
    )
    yield
    logger.info("event=shutdown")


app = FastAPI(
    title="Pricing — Parking Management",
    version=__version__,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
    # Lets the browser front read the correlation ID of a response.
    expose_headers=[CORRELATION_HEADER],
    allow_credentials=False,
)

app.middleware("http")(security_headers_middleware)
# Wraps every other middleware and sees the final status.
app.middleware("http")(request_logging_middleware)
# Registered last (outermost) so the request log line already carries the correlation ID.
app.middleware("http")(correlation_id_middleware)

register_error_handlers(app)

app.include_router(root.router)
app.include_router(health.router)
app.include_router(metrics_router.router)
app.include_router(quotes.router)
app.include_router(rates.router)
app.include_router(grids.router)
app.include_router(settings_router.router)
