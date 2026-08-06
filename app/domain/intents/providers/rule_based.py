"""
HunterOS Engage V1 - Rule-Based Intent Detector Provider
Evaluates registered rule packs and compiles detailed RuleExecutionReport telemetry.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import DetectedIntent, RuleExecutionReport
from app.domain.intents.providers.base import IntentDetectorProvider
from app.domain.intents.rules.registry import (
    IntentRulePackRegistry,
    default_rule_pack_registry,
)


class RuleBasedIntentDetectorProvider(IntentDetectorProvider):
    """Executes deterministic rules from registered rule packs."""

    def __init__(self, registry: Optional[IntentRulePackRegistry] = None):
        self._registry = registry or default_rule_pack_registry

    @property
    def provider_name(self) -> str:
        return "RuleBasedIntentDetectorProvider"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def detect_candidates(
        self, context: IntentDetectionContext
    ) -> Tuple[List[DetectedIntent], RuleExecutionReport]:
        start = time.perf_counter()
        rules = self._registry.get_all_rules()

        candidates: List[DetectedIntent] = []
        executed_rules: List[str] = []
        matched_rules: List[str] = []
        rejected_rules: List[str] = []
        rule_match_details: Dict[str, Any] = {}

        for rule in rules:
            executed_rules.append(rule.rule_name)
            try:
                rule_intents = rule.evaluate(context)
                if rule_intents:
                    matched_rules.append(rule.rule_name)
                    rule_match_details[rule.rule_name] = {
                        "count": len(rule_intents),
                        "types": [i.intent_type.value for i in rule_intents],
                    }
                    candidates.extend(rule_intents)
                else:
                    rejected_rules.append(rule.rule_name)
            except Exception as e:
                rejected_rules.append(rule.rule_name)
                rule_match_details[rule.rule_name] = {"error": str(e)}
                context.add_warning(f"Rule '{rule.rule_name}' error during evaluation: {e}")

        duration_ms = round((time.perf_counter() - start) * 1000.0, 3)

        report = RuleExecutionReport(
            executed_rules=executed_rules,
            matched_rules=matched_rules,
            rejected_rules=rejected_rules,
            execution_time_ms=duration_ms,
            conflict_count=0,
            rule_match_details=rule_match_details,
        )

        return candidates, report
