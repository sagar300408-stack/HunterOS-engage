from typing import Dict, List, Type
from .base import AbstractRecommendationExplanationRule

class RecommendationExplanationRuleRegistry:
    _rules: Dict[str, Type[AbstractRecommendationExplanationRule]] = {}

    @classmethod
    def register(cls, name: str, rule_cls: Type[AbstractRecommendationExplanationRule]):
        cls._rules[name] = rule_cls

    @classmethod
    def get_rule(cls, name: str) -> Type[AbstractRecommendationExplanationRule]:
        if name not in cls._rules:
            raise KeyError(f"Rule {name} not found in registry")
        return cls._rules[name]

    @classmethod
    def get_all_rules(cls) -> List[AbstractRecommendationExplanationRule]:
        return [rule_cls() for rule_cls in cls._rules.values()]
