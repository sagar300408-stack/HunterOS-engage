"""
HunterOS Engage — Analysis Validation Framework (Phase 2.2.1)

Validates source message provenance, confidence bounds, schema integrity,
and boundary invariants across all analysis artifacts.
"""

from __future__ import annotations

from typing import Any, List, Set

from app.domain.conversations.analysis.context import ConversationAnalysisContext


class AnalysisValidationFramework:
    """
    Validates structural correctness, lineage traceability, and invariants
    of the ConversationAnalysisContext before final output generation.
    """

    def validate(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        valid_message_ids: Set[str] = {m.id for m in context.normalized_messages}

        # 1. Source Message Traceability Validation
        self._validate_fact_sources(context, valid_message_ids)
        self._validate_segment_sources(context, valid_message_ids)
        self._validate_topic_sources(context, valid_message_ids)

        # 2. Confidence Bounds Validation
        self._validate_confidence_bounds(context)

        # 3. Fact Canonical Integrity
        self._validate_fact_canonical_values(context)

        # 4. Strict Non-Mutating Architectural Invariants
        self._validate_architectural_boundaries(context)

        return context

    def _validate_fact_sources(self, context: ConversationAnalysisContext, valid_ids: Set[str]) -> None:
        for fact in context.facts:
            for src in fact.provenance.source_messages:
                if valid_ids and src.message_id not in valid_ids:
                    context.add_warning(
                        f"Fact [{fact.key}] references non-existent message ID [{src.message_id}]."
                    )

    def _validate_segment_sources(self, context: ConversationAnalysisContext, valid_ids: Set[str]) -> None:
        for seg in context.segments:
            if valid_ids and seg.start_message_id not in valid_ids:
                context.add_warning(
                    f"Segment [{seg.segment_type.value}] start message [{seg.start_message_id}] not found."
                )
            if valid_ids and seg.end_message_id not in valid_ids:
                context.add_warning(
                    f"Segment [{seg.segment_type.value}] end message [{seg.end_message_id}] not found."
                )

    def _validate_topic_sources(self, context: ConversationAnalysisContext, valid_ids: Set[str]) -> None:
        if context.topics:
            for dist in context.topics.distribution:
                if not (0.0 <= dist.provenance.confidence <= 1.0):
                    context.add_error(f"Topic [{dist.topic_name}] confidence out of bounds: {dist.provenance.confidence}")

    def _validate_confidence_bounds(self, context: ConversationAnalysisContext) -> None:
        for fact in context.facts:
            if not (0.0 <= fact.provenance.confidence <= 1.0):
                context.add_error(
                    f"Fact [{fact.key}] has invalid confidence: {fact.provenance.confidence} (must be between 0.0 and 1.0)"
                )
        for seg in context.segments:
            if not (0.0 <= seg.provenance.confidence <= 1.0):
                context.add_error(
                    f"Segment [{seg.segment_type.value}] has invalid confidence: {seg.provenance.confidence}"
                )

    def _validate_fact_canonical_values(self, context: ConversationAnalysisContext) -> None:
        for fact in context.facts:
            if fact.canonical_value is None or fact.canonical_value.data_type is None:
                context.add_error(f"Fact [{fact.key}] missing canonical value or data_type.")

    def _validate_architectural_boundaries(self, context: ConversationAnalysisContext) -> None:
        """Verify no illegal generative, intent, recommendation or memory fields leaked into artifacts."""
        # Conversation Analysis must remain purely descriptive
        forbidden_keys = {"predicted_intent", "recommendation_actions", "memory_commands", "journey_state"}
        for k in forbidden_keys:
            if k in context.artifacts:
                context.add_error(f"Illegal field [{k}] detected in Conversation Analysis context.")
