from zayd_common.health import HealthStatus
from zayd_common.settings import ServiceSettings


def get_health() -> HealthStatus:
    settings = ServiceSettings(app_name="ingestion")
    return HealthStatus(service=settings.app_name)
