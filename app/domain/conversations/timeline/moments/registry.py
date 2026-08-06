"""
HunterOS Engage V1 - Important Moment Registry
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Extensible registry maintaining and evaluating important moment rules.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import ImportantMoment
from app.domain.conversations.timeline.moments.base import AbstractImportantMomentRule
from app.domain.conversations.timeline.moments.standard import (
    BudgetDiscussionMomentRule,
    CustomerDecisionMomentRule,
    CustomMomentRule,
    DocumentExchangeMomentRule,
    FirstCommitmentMomentRule,
    FirstObjectionMomentRule,
    FirstRequirementMomentRule,
    MeetingConfirmationMomentRule,
)

logger = logging.getLogger(__name__)


class ImportantMomentRegistry:
    """Registry maintaining and orchestrating pluggable important moment rules."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._rules: Dict[str, AbstractImportantMomentRule] = {}
        if register_defaults:
            self._register_default_rules()

    def _register_default_rules(self) -> None:
        defaults: List[AbstractImportantMomentRule] = [
            FirstRequirementMomentRule(),
            BudgetDiscussionMomentRule(),
            FirstCommitmentMomentRule(),
            FirstObjectionMomentRule(),
            DocumentExchangeMomentRule(),
            MeetingConfirmationMomentRule(),
            CustomerDecisionMomentRule(),
            CustomMomentRule(),
        ]
        for rule in defaults:
            self.register(rule)

    def register(self, rule: AbstractImportantMomentRule) -> None:
        """Registers an important moment detection rule."""
        self._rules[rule.rule_name] = rule
        logger.debug("Registered important moment rule: %s", rule.rule_name)

    def unregister(self, rule_name: str) -> Optional[AbstractImportantMomentRule]:
        """Unregisters an important moment rule."""
        return self._rules.pop(rule_name, None)

    def get(self, rule_name: str) -> Optional[AbstractImportantMomentRule]:
        """Retrieves a rule by name."""
        return self._rules.get(rule_name)

    def list_rules(self) -> List[str]:
        """Returns all registered rule names."""
        return list(self._rules.keys())

    def evaluate_all(self, context: ConversationTimelineContext) -> List[ImportantMoment]:
        """Evaluates all moment rules against context and returns detected moments sorted chronologically."""
        moments: List[ImportantMoment] = []
        for name, rule in self._rules.items():
            try:
                moment = rule.evaluate(context)
                if moment:
                    moments.append(moment)
            except Exception as e:
                logger.error("Error evaluating important moment rule %s: %s", name, str(e), exc_info=True)
                context.add_warning(f"Important moment rule {name} failed: {str(e)}")

        moments.sort(key=lambda m: m.timestamp)
        return moments


# Global default singleton instance
default_important_moment_registry = ImportantMomentRegistry()
