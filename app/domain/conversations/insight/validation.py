"""
HunterOS Engage V1 - Insight Validation Framework
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Enforces structural invariants, evidence completeness, reference integrity,
cross-workspace isolation, and strict architectural boundary guards.
"""

from __future__ import annotations

import logging
from typing import List, Set

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import (
    ConversationInsight,
    ConversationInsightResult,
    InsightEvidence,
)

logger = logging.getLogger(__name__)

# Forbidden keys that must NEVER appear in conversation insights
FORBIDDEN_DOMAIN_KEYS = {
    "memory_update",
    "sentiment_score",
    "sentiment",
    "intent",
    "customer_journey_stage",
    "lead_score",
    "recommendation_action",
    "workflow_trigger",
    "autonomous_decision",
    "recommendation",
}


class InsightValidationFramework:
    """Validates structural and architectural invariants for conversation insights."""

    def validate_context(self, context: ConversationInsightContext) -> List[str]:
        """Runs full validation suite on context before output synthesis."""
        errors: List[str] = []

        # 1. Evidence Completeness Check
        for ins in context.all_insights:
            if not self._has_valid_evidence(ins.evidence):
                errors.append(f"Insight {ins.insight_id} ({ins.title}) lacks mandatory supporting evidence.")

        # 2. Reference Integrity Check
        valid_msg_ids = self._collect_valid_message_ids(context)
        valid_event_ids = {e.event_id for e in context.get_events()}
        valid_fact_ids = {f.fact_id for f in context.get_facts()}

        for ins in context.all_insights:
            for mid in ins.evidence.source_message_ids:
                if valid_msg_ids and mid not in valid_msg_ids:
                    context.add_warning(f"Insight {ins.insight_id} references unverified message_id '{mid}'.")
            for eid in ins.evidence.source_event_ids:
                if valid_event_ids and eid not in valid_event_ids:
                    errors.append(f"Insight {ins.insight_id} references non-existent event_id '{eid}'.")
            for fid in ins.evidence.fact_ids:
                if valid_fact_ids and fid not in valid_fact_ids:
                    errors.append(f"Insight {ins.insight_id} references non-existent fact_id '{fid}'.")

        # 3. Confidence Bounds Check
        for ins in context.all_insights:
            if not (0.0 <= ins.confidence <= 1.0):
                errors.append(f"Insight {ins.insight_id} has invalid confidence score {ins.confidence}.")

        # 4. Strict Architectural Boundary Guard
        for ins in context.all_insights:
            self._check_forbidden_keys(ins.metadata, f"Insight {ins.insight_id}", errors)

        # 5. Cross-Workspace Isolation Check
        if context.analysis_result and context.timeline:
            if (
                context.analysis_result.workspace_id
                and context.timeline.workspace_id
                and context.analysis_result.workspace_id != context.timeline.workspace_id
            ):
                errors.append(
                    f"Cross-workspace contamination: analysis workspace {context.analysis_result.workspace_id} "
                    f"!= timeline workspace {context.timeline.workspace_id}."
                )

        return errors

    def validate_result(self, result: ConversationInsightResult) -> List[str]:
        """Validates an aggregate root directly."""
        errors: List[str] = []

        if not result.conversation_id:
            errors.append("InsightResult missing mandatory conversation_id.")

        for ins in result.all_insights:
            if not self._has_valid_evidence(ins.evidence):
                errors.append(f"Insight {ins.insight_id} lacks supporting evidence.")
            self._check_forbidden_keys(ins.metadata, f"Insight {ins.insight_id}", errors)

        return errors

    def deduplicate_insights(self, context: ConversationInsightContext) -> None:
        """Removes duplicate insights based on category and normalized title."""
        seen_keys: Set[str] = set()

        deduped_risks = []
        for r in context.classified_risks:
            key = f"RISK:{r.category.value}:{r.title.strip().lower()}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_risks.append(r)
        context.classified_risks = deduped_risks

        deduped_opps = []
        for o in context.classified_opportunities:
            key = f"OPP:{o.category.value}:{o.title.strip().lower()}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_opps.append(o)
        context.classified_opportunities = deduped_opps

        deduped_actions = []
        for a in context.classified_action_items:
            key = f"ACTION:{a.category.value}:{a.title.strip().lower()}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_actions.append(a)
        context.classified_action_items = deduped_actions

        deduped_all = []
        seen_all: Set[str] = set()
        for ins in context.all_insights:
            key = f"{ins.insight_type.value}:{ins.category.value}:{ins.title.strip().lower()}"
            if key not in seen_all:
                seen_all.add(key)
                deduped_all.append(ins)
        context.all_insights = deduped_all

    def _has_valid_evidence(self, evidence: InsightEvidence) -> bool:
        """Checks if evidence has at least one concrete citation link."""
        return bool(
            evidence.source_message_ids
            or evidence.source_event_ids
            or evidence.source_milestone_ids
            or evidence.source_moment_ids
            or evidence.fact_ids
            or evidence.topics
            or evidence.text_snippets
        )

    def _collect_valid_message_ids(self, context: ConversationInsightContext) -> Set[str]:
        """Collects all valid source message IDs across input artifacts."""
        msg_ids: Set[str] = set()
        if context.analysis_result:
            for s in context.analysis_result.segments or []:
                msg_ids.update(s.message_ids)
            for f in context.analysis_result.facts or []:
                msg_ids.update(f.source_message_ids)
        if context.timeline and context.timeline.event_stream:
            for e in context.timeline.event_stream.events:
                msg_ids.update(e.provenance.source_message_ids)
        return msg_ids

    def _check_forbidden_keys(self, data: dict, location: str, errors: List[str]) -> None:
        """Verifies no forbidden domain keys leaked into metadata."""
        for k in data.keys():
            if k.lower() in FORBIDDEN_DOMAIN_KEYS:
                errors.append(f"{location} contains forbidden architectural key: '{k}'")


default_insight_validation_framework = InsightValidationFramework()
