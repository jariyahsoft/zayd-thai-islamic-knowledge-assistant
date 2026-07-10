import signal
import time

from zayd_common.logging import (
    bind_request_context,
    configure_logging,
    get_logger,
    new_trace_context,
)
from zayd_common.telemetry import telemetry_registry

from .service import get_health

logger = get_logger("zayd.worker")
running = True


def _handle_shutdown(signum: int, _frame: object | None) -> None:
    global running
    with bind_request_context(new_trace_context(service="worker", source="generated")):
        logger.info("worker_shutdown signal=%s", signum)
    running = False


def main() -> int:
    configure_logging()
    health = get_health()
    with bind_request_context(new_trace_context(service=health.service, source="generated")):
        with telemetry_registry.span(
            "worker.lifecycle",
            attributes={"service": health.service, "status": health.status},
        ):
            logger.info("worker_started service=%s status=%s", health.service, health.status)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    while running:
        time.sleep(30)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
