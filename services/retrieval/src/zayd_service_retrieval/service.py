from zayd_common.health import HealthStatus
from zayd_common.settings import ServiceSettings


def get_health() -> HealthStatus:
    settings = ServiceSettings.from_runtime_env(app_name="retrieval")
    return HealthStatus(service=settings.app_name)
