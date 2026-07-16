from app.domain.health.evaluators.registry import health_registry
from app.domain.health.evaluators.standard_health import SalesHealthEvaluator, CustomerEngagementHealthEvaluator


def bootstrap_health():
    """
    Registers all standard Operational Health evaluators in the global registry.
    """
    health_registry.register(SalesHealthEvaluator())
    health_registry.register(CustomerEngagementHealthEvaluator())
