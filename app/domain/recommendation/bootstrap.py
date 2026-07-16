from app.domain.recommendation.generators.registry import recommendation_registry
from app.domain.recommendation.generators.standard_recommendations import DecliningEngagementGenerator, PipelineBottleneckGenerator


def bootstrap_recommendations():
    """
    Registers all standard Recommendation Generators in the global registry.
    """
    recommendation_registry.register(DecliningEngagementGenerator())
    recommendation_registry.register(PipelineBottleneckGenerator())
