from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from io import TextIOBase
from typing import Any, Literal, cast
from uuid import uuid4

TraceContextSource = Literal["generated", "header", "manual"]

_SECRET_KEYWORDS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "prompt",
    "provider_key",
    "secret",
    "session",
    "signed_url",
    "token",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer\s+[a-z0-9._\-]+)"),
    re.compile(r"(?i)\b(sk-[a-z0-9_\-]+)"),
    re.compile(r"(?i)\b(xox[baprs]-[a-z0-9\-]+)"),
)

_request_id_var: ContextVar[str | None] = ContextVar("zayd_request_id", default=None)
_trace_id_var: ContextVar[str | None] = ContextVar("zayd_trace_id", default=None)
_service_var: ContextVar[str | None] = ContextVar("zayd_service_name", default=None)


@dataclass(frozen=True)
class TraceContext:
    request_id: str
    trace_id: str
    source: TraceContextSource
    service: str | None = None


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_value(record.getMessage()),
        }
        service = getattr(record, "service", None) or current_service_name()
        if service:
            payload["service"] = service
        request_id = getattr(record, "request_id", None) or current_request_id()
        if request_id:
            payload["request_id"] = request_id
        trace_id = getattr(record, "trace_id", None) or current_trace_id()
        if trace_id:
            payload["trace_id"] = trace_id
        if hasattr(record, "event"):
            payload["event"] = redact_value(record.event)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class SafeStreamHandler(logging.StreamHandler[TextIOBase]):
    def __init__(self, stream: TextIOBase | None = None) -> None:
        resolved_stream = stream if stream is not None else cast(TextIOBase, sys.stderr)
        super().__init__(resolved_stream)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = current_request_id()
        if not hasattr(record, "trace_id"):
            record.trace_id = current_trace_id()
        if not hasattr(record, "service"):
            record.service = current_service_name()
        return True


def _stderr_handler() -> logging.Handler:
    handler = SafeStreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(RequestContextFilter())
    return handler


def configure_logging(*, level: str = "INFO") -> None:
    normalized_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(normalized_level)
    if not any(getattr(handler, "_zayd_structured", False) for handler in root.handlers):
        handler = _stderr_handler()
        handler._zayd_structured = True  # type: ignore[attr-defined]
        root.handlers.clear()
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setLevel(normalized_level)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, RequestContextFilter) for f in logger.filters):
        logger.addFilter(RequestContextFilter())
    if not logger.handlers and not logging.getLogger().handlers:
        configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    return logger


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > 128:
        trimmed = trimmed[:128]
    safe = "".join(char for char in trimmed if char.isalnum() or char in "-_.:/")
    return safe or None


def new_trace_context(
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    source: TraceContextSource = "generated",
    service: str | None = None,
) -> TraceContext:
    normalized_request = normalize_request_id(request_id) or f"req-{uuid4().hex}"
    normalized_trace = normalize_request_id(trace_id) or normalized_request
    return TraceContext(
        request_id=normalized_request,
        trace_id=normalized_trace,
        source=source,
        service=service,
    )


@contextmanager
def bind_request_context(context: TraceContext) -> Any:
    request_token: Token[str | None] = _request_id_var.set(context.request_id)
    trace_token: Token[str | None] = _trace_id_var.set(context.trace_id)
    service_token: Token[str | None] | None = None
    if context.service is not None:
        service_token = _service_var.set(context.service)
    try:
        yield context
    finally:
        _request_id_var.reset(request_token)
        _trace_id_var.reset(trace_token)
        if service_token is not None:
            _service_var.reset(service_token)


def current_request_id() -> str | None:
    return _request_id_var.get()


def current_trace_id() -> str | None:
    return _trace_id_var.get()


def current_service_name() -> str | None:
    return _service_var.get()


def set_service_name(service: str) -> None:
    _service_var.set(service)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): redact_field(str(key), item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def redact_field(field_name: str, value: Any) -> Any:
    lower = field_name.lower()
    if any(keyword in lower for keyword in _SECRET_KEYWORDS):
        return "[redacted]"
    return redact_value(value)


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


__all__ = [
    "TraceContext",
    "bind_request_context",
    "configure_logging",
    "current_request_id",
    "current_service_name",
    "current_trace_id",
    "get_logger",
    "new_trace_context",
    "normalize_request_id",
    "redact_field",
    "redact_value",
    "set_service_name",
]
