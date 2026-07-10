import io
import json
import logging

from zayd_common.logging import SafeStreamHandler, StructuredJsonFormatter
from zayd_service_worker import get_health
from zayd_service_worker.main import _handle_shutdown


def test_worker_imports() -> None:
    assert get_health().service == "worker"


def test_worker_shutdown_log_keeps_request_context() -> None:
    stream = io.StringIO()
    handler = SafeStreamHandler(stream)
    handler.setFormatter(StructuredJsonFormatter())
    logger = logging.getLogger("zayd.worker")
    original_handlers = list(logger.handlers)
    original_propagate = logger.propagate
    logger.handlers = [handler]
    logger.propagate = False
    try:
        _handle_shutdown(15, None)
    finally:
        logger.handlers = original_handlers
        logger.propagate = original_propagate

    payload = json.loads(stream.getvalue().strip())
    assert payload["logger"] == "zayd.worker"
    assert payload["request_id"].startswith("req-")
    assert payload["trace_id"] == payload["request_id"]
