import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event_name", record.getMessage()),
        }
        payload.update(getattr(record, "event_data", {}))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    root = logging.getLogger()
    if any(getattr(handler, "_aiprod_handler", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._aiprod_handler = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(
    logger: logging.Logger,
    event_name: str,
    *,
    level: int = logging.INFO,
    **data: object,
) -> None:
    logger.log(level, event_name, extra={"event_name": event_name, "event_data": data})

