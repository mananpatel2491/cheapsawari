"""Observability foundation — structured, queryable application logging (Slice 11).

One small, dependency-free layer so every part of the app logs the same way and the
*what* is decoupled from the *how*:

    from . import obs
    _log = obs.get_logger("auth")
    obs.event(_log, "auth.login", outcome="ok", provider="google", email=email)

Design goals (so logging is easy to change later):
- **Structured**: on Cloud Run each line is JSON (`{"severity","message","event",<fields>}`),
  which Cloud Logging parses into `jsonPayload.*` — so you query by field, e.g.
  `jsonPayload.event="auth.login" AND jsonPayload.outcome="denied"`. Locally it's compact
  human text instead.
- **Flexible**: `event()` takes arbitrary keyword fields. Logging more or fewer details is
  a one-line change at the call site (add/remove a kwarg) — no formatter or schema edits.
  Verbosity is env-controlled (`LOG_LEVEL`), so you can dial detail up/down without code.
- **Isolated**: only the `cheapsawari` logger tree is configured (propagate disabled), so we
  never fight uvicorn's own access/error logging.

To add a new event: pick a dotted `name` ("domain.action"), call `obs.event(...)`, and add a
row to `docs/LOGGING.md`. To add a field everywhere (e.g. a request/trace id), set it once in
a contextvar and merge it in `_JsonFormatter.format` — every event gains it, no call-site churn.
"""
from __future__ import annotations

import json
import logging
import os
import sys

_ROOT_NAME = "cheapsawari"

# Cloud Run sets K_SERVICE; use JSON there so Cloud Logging gets structured fields.
_ON_CLOUD_RUN = bool(os.getenv("K_SERVICE"))

# Python level -> Cloud Logging severity string (read from the "severity" JSON key).
_SEVERITY = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}

# Reserved so a stray field name can't clobber the envelope.
_RESERVED = {"severity", "message", "logger", "event", "exception"}


class _JsonFormatter(logging.Formatter):
    """One JSON object per line: envelope + the event's structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": _SEVERITY.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
        }
        event = getattr(record, "event", None)
        if event:
            payload["event"] = event
        for key, value in (getattr(record, "fields", None) or {}).items():
            payload[key if key not in _RESERVED else f"field_{key}"] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    """Compact, readable lines for local dev: `LEVEL  logger  event  k=v k=v`."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [f"{record.levelname:<7}", record.name, record.getMessage()]
        fields = getattr(record, "fields", None) or {}
        if fields:
            parts.append(" ".join(f"{k}={v}" for k, v in fields.items()))
        line = "  ".join(p for p in parts if p)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging() -> None:
    """Install the structured handler on the `cheapsawari` logger tree. Idempotent.

    Level comes from `LOG_LEVEL` (default INFO) so you can make the app log more
    (DEBUG) or less (WARNING) without touching code.
    """
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").strip().upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter() if _ON_CLOUD_RUN else _TextFormatter())

    root = logging.getLogger(_ROOT_NAME)
    root.handlers = [handler]  # replace so re-config doesn't duplicate lines
    root.setLevel(level)
    root.propagate = False  # don't double-log via the root/uvicorn handlers


def get_logger(name: str) -> logging.Logger:
    """Return a child logger, e.g. get_logger('auth') -> 'cheapsawari.auth'."""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


def event(
    logger: logging.Logger,
    name: str,
    *,
    level: int = logging.INFO,
    exc_info: bool = False,
    **fields,
) -> None:
    """Emit a structured event. ``name`` is the message + the queryable `event` field;
    ``fields`` are arbitrary structured attributes (None values are dropped)."""
    clean = {k: v for k, v in fields.items() if v is not None}
    logger.log(level, name, extra={"event": name, "fields": clean}, exc_info=exc_info)
