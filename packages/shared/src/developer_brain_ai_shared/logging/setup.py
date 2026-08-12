"""structlog setup central. Configurado uma vez no composition root.

- Em ``dev`` (APP_LOG_JSON=false): console renderer colorido.
- Em ``prod``: JSON renderer p/ ingest em ELK/Loki.

Nao importa logging stdlib global a fora disso; componentes usam
``structlog.get_logger(__name__)`` para criar loggers bound ao contexto.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

LogLevel = str


def configure_logging(level: LogLevel = "INFO", json_output: bool = False) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def bind_context(**kwargs: Any) -> None:
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


__all__ = ["bind_context", "clear_context", "configure_logging", "get_logger"]
