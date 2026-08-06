"""
HunterOS Engage V1 - Milestone Rule Registry
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Extensible registry maintaining and evaluating milestone rules.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.milestones.base import AbstractMilestoneRule
from app.domain.conversations.timeline.milestones.standard import (
    AppointmentCommittedRule,
    BudgetEstablishedRule,
    CommercialTermsRule,
    CommitmentFinalizedRule,
    CustomMilestoneRule,
    InitialEngagementRule,
    NeedsAlignedRule,
    SessionConcludedRule,
)
from app.domain.conversations.timeline.models import TimelineMilestone

logger = logging.getLogger(__name__)


class MilestoneRuleRegistry:
    """Registry maintaining and orchestrating pluggable milestone rules."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._rules: Dict[str, AbstractMilestoneRule] = {}
        if register_defaults:
            self._register_default_rules()

    def _register_default_rules(self) -> None:
        defaults: List[AbstractMilestoneRule] = [
            InitialEngagementRule(),
            NeedsAlignedRule(),
            BudgetEstablishedRule(),
            CommercialTermsRule(),
            AppointmentCommittedRule(),
            CommitmentFinalizedRule(),
            SessionConcludedRule(),
            CustomMilestoneRule(),
        ]
        for rule in defaults:
            self.register(rule)

    def register(self, rule: AbstractMilestoneRule) -> None:
        """Registers a milestone detection rule."""
        self._rules[rule.rule_name] = rule
        logger.debug("Registered milestone rule: %s", rule.rule_name)

    def unregister(self, rule_name: str) -> Optional[AbstractMilestoneRule]:
        """Unregisters a milestone rule."""
        return self._rules.pop(rule_name, None)

    def get(self, rule_name: str) -> Optional[AbstractMilestoneRule]:
        """Retrieves a rule by name."""
        return self._rules.get(rule_name)

    def list_rules(self) -> List[str]:
        """Returns all registered rule names."""
        return list(self._rules.keys())

    def evaluate_all(self, context: ConversationTimelineContext) -> List[TimelineMilestone]:
        """Evaluates all rules against context and returns detected milestones sorted chronologically."""
        milestones: List[TimelineMilestone] = []
        for name, rule in self._rules.items():
            try:
                ms = rule.evaluate(context)
                if ms:
                    milestones.append(ms)
            except Exception as e:
                logger.error("Error evaluating milestone rule %s: %s", name, str(e), exc_info=True)
                context.add_warning(f"Milestone rule {name} failed: {str(e)}")

        milestones.sort(key=lambda m: m.timestamp)
        return milestones


# Global default singleton instance
default_milestone_rule_registry = MilestoneRuleRegistry()
