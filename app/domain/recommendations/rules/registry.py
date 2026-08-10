from __future__ import annotations
import threading
from typing import Dict, List, Optional
from app.domain.recommendations.rules.base import AbstractRecommendationRule

class RecommendationRuleRegistry:
    def __init__(self) -> None:
        self._rules: Dict[str, AbstractRecommendationRule] = {}
        self._lock = threading.RLock()

    def register(self, rule: AbstractRecommendationRule) -> None:
        with self._lock:
            if rule.rule_id in self._rules:
                raise ValueError(f"Rule with ID {rule.rule_id} is already registered.")
            self._rules[rule.rule_id] = rule

    def unregister(self, rule_id: str) -> None:
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]

    def get(self, rule_id: str) -> Optional[AbstractRecommendationRule]:
        with self._lock:
            return self._rules.get(rule_id)

    def exists(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def list_all(self) -> List[AbstractRecommendationRule]:
        with self._lock:
            return list(self._rules.values())
