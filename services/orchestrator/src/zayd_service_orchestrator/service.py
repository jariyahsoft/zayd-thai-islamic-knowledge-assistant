from zayd_common.health import HealthStatus
from zayd_common.settings import ServiceSettings


def get_health() -> HealthStatus:
    settings = ServiceSettings(app_name="orchestrator")
    return HealthStatus(service=settings.app_name)
