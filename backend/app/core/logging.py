import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure application-wide logging.

    Called once at startup. Keeps output structured enough to grep/parse
    while remaining plain text; swap the formatter here if a JSON sink is
    needed later (e.g. shipping logs to an aggregator).
    """
    settings = get_settings()

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root.handlers = [handler]

    # Quiet noisy third-party loggers unless we're in debug mode.
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
