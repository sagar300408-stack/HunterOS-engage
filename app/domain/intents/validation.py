"""
HunterOS Engage V1 - Intent Validation Framework
Strict invariant validation and architectural boundary guardrails for detected intents.
"""

from __future__ import annotations

from typing import List, Set

from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import DetectedIntent, IntentType


class IntentValidator:
    """
    Validates candidate intents against enterprise invariants, evidence completeness,
    and strict architectural boundaries.
    """

    FORBIDDEN_METADATA_KEYS: Set[str] = {
        "sentiment",
        "sentiment_score",
        "sentiment_label",
        "lead_score",
        "lead_qualification_score",
        "journey_stage",
        "journey_mutation",
        "journey_stage_mutation",
        "customer_journey_update",
        "recommendation",
        "recommended_action",
        "autonomous_action",
        "workflow_execution",
        "memory_graph_update",
    }

    def validate_candidate(
        self, intent: DetectedIntent, context: IntentDetectionContext
    ) -> List[str]:
        """
        Validate a single candidate intent.
        Returns:
            List of validation error messages (empty if valid).
        """
        errors: List[str] = []

        # 1. Evidence Completeness
        if not intent.supporting_evidence.has_sufficient_evidence:
            errors.append(
                f"Evidence Completeness Violation: Intent '{intent.intent_type.value}' "
                f"(ID: {intent.intent_id}) lacks any supporting evidence references."
            )

        # 2. Confidence Bounds
        if not (0.0 <= intent.confidence <= 1.0):
            errors.append(
                f"Confidence Bound Violation: Intent '{intent.intent_type.value}' "
                f"has invalid confidence {intent.confidence} (must be between 0.0 and 1.0)."
            )

        # 3. Forbidden Boundary Keys
        for k in intent.metadata.keys():
            if k.lower() in self.FORBIDDEN_METADATA_KEYS:
                errors.append(
                    f"Architectural Boundary Violation: Intent '{intent.intent_type.value}' "
                    f"contains forbidden key '{k}' in metadata."
                )

        # 4. Cross-Workspace Isolation
        if context.workspace_id and intent.workspace_id:
            if context.workspace_id != intent.workspace_id:
                errors.append(
                    f"Cross-Workspace Isolation Violation: Intent workspace '{intent.workspace_id}' "
                    f"does not match context workspace '{context.workspace_id}'."
                )

        # 5. Unsupported Intent Type
        if not isinstance(intent.intent_type, IntentType):
            errors.append(
                f"Unsupported Intent Type Violation: '{intent.intent_type}' is not a valid IntentType."
            )

        return errors

    def validate_context_invariants(self, context: IntentDetectionContext) -> List[str]:
        """
        Validate high-level context invariants across ingested artifacts.
        """
        errors: List[str] = []

        if context.analysis_result and context.timeline:
            analysis_ws = getattr(context.analysis_result, "workspace_id", None)
            timeline_ws = getattr(context.timeline, "workspace_id", None)
            if analysis_ws and timeline_ws and analysis_ws != timeline_ws:
                errors.append(
                    f"Cross-Workspace Contamination: Analysis workspace '{analysis_ws}' "
                    f"differs from Timeline workspace '{timeline_ws}'."
                )

        if context.analysis_result and context.insight_result:
            analysis_ws = getattr(context.analysis_result, "workspace_id", None)
            insight_ws = getattr(context.insight_result, "workspace_id", None)
            if analysis_ws and insight_ws and analysis_ws != insight_ws:
                errors.append(
                    f"Cross-Workspace Contamination: Analysis workspace '{analysis_ws}' "
                    f"differs from Insight workspace '{insight_ws}'."
                )

        return errors


# Default instance
default_intent_validator = IntentValidator()
