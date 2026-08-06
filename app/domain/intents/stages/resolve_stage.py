"""
HunterOS Engage V1 - Resolve Duplicates Stage
Executes IntentResolver to deduplicate and merge multi-source evidence graphs.
"""

from __future__ import annotations

from typing import Optional

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.models import RuleExecutionReport
from app.domain.intents.resolver import IntentResolver, default_intent_resolver
from app.domain.intents.stages.base import IntentPipelineStage


class ResolveDuplicatesStage(IntentPipelineStage):
    """Resolves duplicate intents and merges evidence graphs."""

    def __init__(self, resolver: Optional[IntentResolver] = None):
        self._resolver = resolver or default_intent_resolver

    @property
    def stage_name(self) -> str:
        return "ResolveDuplicatesStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.RESOLVING

    def execute(self, context: IntentDetectionContext) -> None:
        resolved, conflict_count = self._resolver.resolve(context.validated_intents)
        context.resolved_intents = resolved

        # Update rule report conflict count
        rep = context.rule_execution_report
        context.rule_execution_report = RuleExecutionReport(
            executed_rules=rep.executed_rules,
            matched_rules=rep.matched_rules,
            rejected_rules=rep.rejected_rules,
            execution_time_ms=rep.execution_time_ms,
            conflict_count=conflict_count,
            rule_match_details=rep.rule_match_details,
        )
