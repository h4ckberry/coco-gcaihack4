import logging
import logging.config
import os

def configure_logging():
    """Configures logging to reduce verbosity from third-party libraries."""

    # Check if we are in local debug mode to potentially allow more logs,
    # but for now we follow the plan to reduce noise.

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Root logger
            "": {
                "handlers": ["console"],
                "level": "INFO",
            },
            # Application logs - keep at INFO
            "app": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            # Noisy libraries - silence them by setting to WARNING or ERROR
            "opentelemetry": {"level": "WARNING"},
            "google": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
            "grpc": {"level": "WARNING"},
            "asyncio": {"level": "WARNING"},
            "werkzeug": {"level": "WARNING"},
            "uvicorn": {"level": "WARNING"},
            "hpack": {"level": "WARNING"},
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
