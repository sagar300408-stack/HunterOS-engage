"""
HunterOS Engage V1 - Insight Classification Framework
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Normalizes, enriches, and structures detected risks, opportunities, and action items
into a unified polymorphic insight catalog with strict descriptive priority bounds.
"""

from __future__ import annotations

import logging
from typing import List

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ConversationInsight,
    InsightPriority,
    InsightType,
    OpportunityInsight,
    RiskInsight,
)

logger = logging.getLogger(__name__)


class InsightClassifier:
    """
    Classifies and harmonizes candidate insights into standardized entities.
    Ensures deterministic priority grading and builds unified ConversationInsight wrappers.
    """

    def classify_and_harmonize(self, context: ConversationInsightContext) -> None:
        """
        Processes raw risks, opportunities, and action items from context,
        refines priorities and confidence, and constructs the unified polymorphic catalog.
        """
        # Harmonize risks
        classified_risks: List[RiskInsight] = []
        for r in context.raw_risks:
            conf = max(0.0, min(1.0, r.confidence))
            prio = self._evaluate_priority(r.priority, conf, len(r.evidence.source_message_ids))
            classified_risks.append(r.model_copy(update={"priority": prio, "confidence": conf}))
        context.classified_risks = classified_risks

        # Harmonize opportunities
        classified_opps: List[OpportunityInsight] = []
        for o in context.raw_opportunities:
            conf = max(0.0, min(1.0, o.confidence))
            prio = self._evaluate_priority(o.priority, conf, len(o.evidence.source_message_ids))
            classified_opps.append(o.model_copy(update={"priority": prio, "confidence": conf}))
        context.classified_opportunities = classified_opps

        # Harmonize action items
        classified_actions: List[ActionItemInsight] = []
        for a in context.raw_action_items:
            conf = max(0.0, min(1.0, a.confidence))
            prio = self._evaluate_priority(a.priority, conf, len(a.evidence.source_message_ids))
            classified_actions.append(a.model_copy(update={"priority": prio, "confidence": conf}))
        context.classified_action_items = classified_actions

        # Build unified polymorphic collection
        unified: List[ConversationInsight] = []

        for r in classified_risks:
            unified.append(
                ConversationInsight(
                    insight_id=r.risk_id,
                    insight_type=InsightType.RISK,
                    category=r.category,
                    title=r.title,
                    description=r.description,
                    priority=r.priority,
                    confidence=r.confidence,
                    evidence=r.evidence,
                    metadata={"impact_description": r.impact_description, **r.metadata},
                    created_at=r.created_at,
                )
            )

        for o in classified_opps:
            unified.append(
                ConversationInsight(
                    insight_id=o.opportunity_id,
                    insight_type=InsightType.OPPORTUNITY,
                    category=o.category,
                    title=o.title,
                    description=o.description,
                    priority=o.priority,
                    confidence=o.confidence,
                    evidence=o.evidence,
                    metadata={"value_potential": o.value_potential, "qualification_criteria": o.qualification_criteria, **o.metadata},
                    created_at=o.created_at,
                )
            )

        for a in classified_actions:
            unified.append(
                ConversationInsight(
                    insight_id=a.action_id,
                    insight_type=InsightType.ACTION_ITEM,
                    category=a.category,
                    title=a.title,
                    description=a.description,
                    priority=a.priority,
                    confidence=a.confidence,
                    evidence=a.evidence,
                    metadata={"owner_type": a.owner_type.value, "due_date_hint": a.due_date_hint, **a.metadata},
                    created_at=a.created_at,
                )
            )

        context.all_insights = unified
        logger.debug(
            "Harmonized insights for %s: %d risks, %d opps, %d actions (%d total)",
            context.conversation_id,
            len(classified_risks),
            len(classified_opps),
            len(classified_actions),
            len(unified),
        )

    def _evaluate_priority(
        self,
        base_priority: InsightPriority,
        confidence: float,
        evidence_count: int,
    ) -> InsightPriority:
        """Determines final descriptive priority based on confidence and evidence backing."""
        if base_priority == InsightPriority.CRITICAL and confidence >= 0.90:
            return InsightPriority.CRITICAL
        elif base_priority in (InsightPriority.CRITICAL, InsightPriority.HIGH) and confidence >= 0.70:
            return InsightPriority.HIGH
        elif base_priority == InsightPriority.LOW:
            return InsightPriority.LOW
        return InsightPriority.MEDIUM


default_insight_classifier = InsightClassifier()
