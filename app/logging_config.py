"""Logging setup — one line per event, key=value pairs, written to stdout."""

import logging
import sys

from app.correlation import get_correlation_id

LOG_FORMAT = (
    "%(asctime)s level=%(levelname)s logger=%(name)s correlation_id=%(correlation_id)s %(message)s"
)

_base_record_factory = logging.getLogRecordFactory()


def _record_with_correlation_id(*args, **kwargs) -> logging.LogRecord:
    """Attach the current correlation ID to every log record ("-" outside a request)."""
    record = _base_record_factory(*args, **kwargs)
    record.correlation_id = get_correlation_id() or "-"
    return record


def configure_logging(level: str) -> None:
    logging.setLogRecordFactory(_record_with_correlation_id)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Replaced by our own request log, which also records the duration.
    logging.getLogger("uvicorn.access").disabled = True
