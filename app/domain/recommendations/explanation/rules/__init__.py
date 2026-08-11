from .base import AbstractRecommendationExplanationRule, ExplanationSection
from .registry import RecommendationExplanationRuleRegistry

# This file will export the base classes and registry for easy access
__all__ = [
    "AbstractRecommendationExplanationRule",
    "ExplanationSection",
    "RecommendationExplanationRuleRegistry",
]
