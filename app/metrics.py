"""Prometheus metrics, exposed in text format on GET /metrics.

Values live in memory: they restart at zero when the service restarts, which
Prometheus handles natively for counters. Reading them never queries the
database, so frequent scraping does not keep the Neon database awake.

Label values are always bounded (route templates, known zones, error codes),
never raw user input, to keep the number of time series small.
"""

from decimal import Decimal

from prometheus_client import Counter, Gauge, Histogram, Info, disable_created_metrics

from app import __version__
from app.config import settings

# Drop the extra "*_created" timestamp series: they double the output for no use here.
disable_created_metrics()

# ---------- Technical ----------

HTTP_REQUESTS = Counter(
    "pricing_http_requests_total",
    "HTTP requests handled, by method, route template and status code.",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "pricing_http_request_duration_seconds",
    "HTTP request duration in seconds, by method and route template.",
    ["method", "route"],
)

BUILD_INFO = Info("pricing_build", "Version and git commit of the running service.")
BUILD_INFO.info({"version": __version__, "commit": settings.git_commit})

# ---------- Business ----------

QUOTES_COMPUTED = Counter(
    "pricing_quotes_computed_total",
    "Quotes computed, by zone and mode.",
    ["zone", "mode"],
)

QUOTE_AMOUNT = Histogram(
    "pricing_quote_amount_eur",
    "Amount of computed quotes in EUR, by mode.",
    ["mode"],
    buckets=(0, 1, 2, 5, 10, 20, 50, 100, 250, 500),
)

DOMAIN_ERRORS = Counter(
    "pricing_domain_errors_total",
    "Requests refused by a business rule, by error code.",
    ["code"],
)

GRID_PUBLICATIONS = Counter(
    "pricing_grid_publications_total",
    "Price grid versions published, by type of change.",
    ["change"],
)

ACTIVE_GRID_VERSION = Gauge(
    "pricing_active_grid_version",
    "Version number of the price grid currently in force.",
)

ADMIN_AUTH_FAILURES = Counter(
    "pricing_admin_auth_failures_total",
    "Rejected admin calls, by reason.",
    ["reason"],
)


def record_http_request(method: str, route: str, status: int, duration_s: float) -> None:
    HTTP_REQUESTS.labels(method=method, route=route, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(duration_s)


def record_quote(zone: str, mode: str, amount_eur: Decimal) -> None:
    QUOTES_COMPUTED.labels(zone=zone, mode=mode).inc()
    QUOTE_AMOUNT.labels(mode=mode).observe(float(amount_eur))


def record_grid_published(change: str, version: int) -> None:
    GRID_PUBLICATIONS.labels(change=change).inc()
    ACTIVE_GRID_VERSION.set(version)


def set_active_grid_version(version: int) -> None:
    ACTIVE_GRID_VERSION.set(version)


def record_domain_error(code: str) -> None:
    DOMAIN_ERRORS.labels(code=code).inc()


def record_admin_auth_failure(reason: str) -> None:
    ADMIN_AUTH_FAILURES.labels(reason=reason).inc()
