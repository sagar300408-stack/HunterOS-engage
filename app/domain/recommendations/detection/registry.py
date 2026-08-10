import threading
from typing import Dict, List, Any, Optional

from .context import RecommendationDetectionContext
from .models import RecommendationCandidate

class RecommendationDetectionRuleRegistry:
    def __init__(self):
        self._rules: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def register(self, rule_id: str, rule: Any) -> None:
        with self._lock:
            self._rules[rule_id] = rule

    def unregister(self, rule_id: str) -> None:
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]

    def get(self, rule_id: str) -> Optional[Any]:
        with self._lock:
            return self._rules.get(rule_id)

    def exists(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def list(self) -> List[Any]:
        with self._lock:
            return list(self._rules.values())

    def evaluate_all(self, context: RecommendationDetectionContext) -> List[RecommendationCandidate]:
        candidates = []
        with self._lock:
            rules_to_evaluate = list(self._rules.values())
            
        for rule in rules_to_evaluate:
            if hasattr(rule, 'evaluate'):
                rule_candidates = rule.evaluate(context)
                if rule_candidates:
                    candidates.extend(rule_candidates)
                    
        return candidates
