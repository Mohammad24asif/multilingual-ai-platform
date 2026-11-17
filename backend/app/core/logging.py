"""Structured JSON logging that cannot leak user text.

Rules (see SECURITY.md):
* Log lengths, ids, timings, model ids - never the text itself.
* Any field whose name looks like content is replaced by ``<redacted len=N>`` before it is written.
* Exceptions are logged as type + frames (file:line in function) without the exception message,
  because library messages sometimes quote their input.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "text", "source_text", "target_text", "translation", "output", "input", "content", "prompt",
        "body", "message", "question", "answer", "context", "document", "sentence", "sentences", "query",
    }
)

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return lowered in SENSITIVE_KEYS or lowered.endswith("_text")


def redact_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in fields.items():
        if _is_sensitive(key):
            size = len(value) if hasattr(value, "__len__") else len(str(value))
            clean[key] = f"<redacted len={size}>"
        elif isinstance(value, Mapping):
            clean[key] = redact_fields(value)
        else:
            clean[key] = value
    return clean


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        fields = getattr(record, "fields", None)
        if isinstance(fields, Mapping):
            payload.update(redact_fields(fields))
        if record.exc_info and record.exc_info[0] is not None:
            exc_type, _exc, tb = record.exc_info
            payload["exc_type"] = exc_type.__name__
            payload["frames"] = [f"{f.filename.split('/')[-1]}:{f.lineno} in {f.name}" for f in traceback.extract_tb(tb)][-8:]
        return json.dumps(payload, ensure_ascii=False, default=str)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"fields": fields})


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter() if json_output else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
