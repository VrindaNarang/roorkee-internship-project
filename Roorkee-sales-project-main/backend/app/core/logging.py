import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure root logging once at process startup.

    Uses a plain stream handler to stdout so logs are captured correctly by
    Docker / any log aggregator, rather than writing to files.
    """
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Quiet down noisy third-party loggers unless we're debugging.
    if settings.log_level.upper() != "DEBUG":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
