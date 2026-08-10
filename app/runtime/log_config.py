from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import LogFormat, Settings

HANDLER_NAME = "orca"

_APP_LOGGER = "app"
_ADOPTED_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

_STANDARD_FIELDS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
}


def _timestamp(created: float) -> str:
    stamped = datetime.fromtimestamp(created, UTC)
    return stamped.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _context(record: logging.LogRecord) -> dict[str, Any]:
    return {k: v for k, v in vars(record).items() if k not in _STANDARD_FIELDS}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_context(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = _context(record)
        rendered = " ".join(f"{k}={v}" for k, v in context.items())
        head = (
            f"{_timestamp(record.created)} {record.levelname:<8} "
            f"{record.name} {record.getMessage()}"
        )
        line = f"{head} {rendered}" if rendered else head
        if record.exc_info:
            return f"{line}\n{self.formatException(record.exc_info)}"
        return line


def _formatter(log_format: LogFormat) -> logging.Formatter:
    return JsonFormatter() if log_format == "json" else TextFormatter()


def _own_handler(root: logging.Logger) -> logging.Handler | None:
    return next((h for h in root.handlers if h.get_name() == HANDLER_NAME), None)


def _adopt(name: str) -> None:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = True


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    handler = _own_handler(root)
    if handler is None:
        handler = logging.StreamHandler()
        handler.set_name(HANDLER_NAME)
        root.addHandler(handler)
    handler.setFormatter(_formatter(settings.log_format))

    root.setLevel(logging.WARNING)
    logging.getLogger(_APP_LOGGER).setLevel(settings.log_level)
    for name in _ADOPTED_LOGGERS:
        _adopt(name)
