"""Structured logging configuration using structlog.

Outputs JSON lines to stdout, compatible with journald and log aggregators.
Uses contextvars for request_id propagation across async calls.
"""

import logging
import os
import sys
from contextvars import ContextVar

import structlog

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Inject request_id from contextvars into every log entry."""
    rid = request_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def setup_logging() -> None:
    """Configure structlog + stdlib logging for JSON output."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Shared processors for both structlog and stdlib
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet down noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
