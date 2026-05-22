import logging
import sys
from datetime import datetime
from typing import Any

import structlog
from structlog.types import Processor

from src.core.config import config_loader


def add_timezone_info(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    timezone = config_loader.timezone
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_dict["timezone"] = timezone
    return event_dict


def configure_logging() -> None:
    log_config = config_loader.logging_config
    log_level = log_config.get("level", "INFO")
    log_format = log_config.get("format", "json")
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
    
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_timezone_info,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


configure_logging()
