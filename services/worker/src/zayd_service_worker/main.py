import signal
import time

from zayd_common.logging import get_logger

from .service import get_health

logger = get_logger("zayd.worker")
running = True


def _handle_shutdown(signum: int, _frame: object | None) -> None:
    global running
    logger.info("worker_shutdown signal=%s", signum)
    running = False


def main() -> int:
    health = get_health()
    logger.info("worker_started service=%s status=%s", health.service, health.status)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    while running:
        time.sleep(30)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
