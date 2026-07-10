from __future__ import annotations

import io
import json
import logging

from zayd_common.logging import (
    SafeStreamHandler,
    StructuredJsonFormatter,
    bind_request_context,
    new_trace_context,
    redact_value,
)


def test_structured_logs_include_request_and_trace_ids() -> None:
    stream = io.StringIO()
    handler = SafeStreamHandler(stream)
    handler.setFormatter(StructuredJsonFormatter())
    logger = logging.getLogger("zayd.tests.logging.structured")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    with bind_request_context(
        new_trace_context(
            request_id="req-123",
            trace_id="trace-123",
            service="api",
            source="manual",
        )
    ):
        logger.info("login ok")

    payload = json.loads(stream.getvalue().strip())
    assert payload["request_id"] == "req-123"
    assert payload["trace_id"] == "trace-123"
    assert payload["service"] == "api"
    assert payload["message"] == "login ok"


def test_redaction_masks_secrets_and_tokens() -> None:
    redacted = redact_value(
        {
            "password": "very-secret",
            "provider_token": "sk-secret-key-12345",
            "nested": {"authorization": "Bearer abc.def"},
            "message": "Authorization: Bearer abc.def",
        }
    )

    assert redacted["password"] == "[redacted]"
    assert redacted["provider_token"] == "[redacted]"
    assert redacted["nested"]["authorization"] == "[redacted]"
    assert "Bearer abc.def" not in redacted["message"]


def test_logging_failure_does_not_raise() -> None:
    class BrokenStream:
        def write(self, _value: str) -> int:
            raise OSError("disk full")

        def flush(self) -> None:
            return None

    handler = SafeStreamHandler(BrokenStream())  # type: ignore[arg-type]
    handler.setFormatter(StructuredJsonFormatter())
    logger = logging.getLogger("zayd.tests.logging.failure")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("still safe")
