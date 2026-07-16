from app.domain.insight.generators.registry import insight_registry
from app.domain.insight.generators.standard_insights import EngagementImprovementGenerator, SalesPipelineGenerator


def bootstrap_insights():
    """
    Registers all standard Insight Generators in the global registry.
    """
    insight_registry.register(EngagementImprovementGenerator())
    insight_registry.register(SalesPipelineGenerator())
