"""Logging setup — one line per event, key=value pairs, written to stdout."""

import logging
import sys

LOG_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Replaced by our own request log, which also records the duration.
    logging.getLogger("uvicorn.access").disabled = True
