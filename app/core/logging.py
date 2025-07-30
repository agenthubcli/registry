"""
Logging configuration for AgentHub Registry.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.typing import EventDict

from app.core.config import settings


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request ID to log events if available."""
    # This would be set by middleware
    request_id = getattr(logging.getLogger(), "request_id", None)
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_service_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service information to log events."""
    event_dict["service"] = "agenthub-registry"
    event_dict["version"] = settings.VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        add_service_info,
        add_request_id,
        structlog.processors.format_exc_info,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.ENVIRONMENT == "development":
        # Pretty console output for development
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    else:
        # JSON output for production
        shared_processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ])
    
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    if settings.ENVIRONMENT == "production":
        # Reduce noise in production
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING) 