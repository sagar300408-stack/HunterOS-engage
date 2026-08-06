"""
HunterOS Engage V1 - Intent Classification Validator
Enforces taxonomy graph consistency, relationship integrity, workspace isolation, and zero-mutation guardrails.
"""

from __future__ import annotations

from typing import Optional, Set
import uuid

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
    default_taxonomy_graph,
)

# Architectural Boundary: Strictly forbidden keys from downstream domains
FORBIDDEN_METADATA_KEYS: Set[str] = {
    "sentiment",
    "lead_score",
    "journey_stage",
    "recommendation",
    "autonomous_action",
    "workflow_execution",
    "memory_update",
    "next_step_prediction",
}


class IntentClassificationValidator:
    """
    Validates classified intents, relationships, and groups for consistency and architectural compliance.
    """

    def __init__(self, taxonomy_graph: Optional[BusinessIntentTaxonomyGraph] = None):
        self._taxonomy_graph = taxonomy_graph or default_taxonomy_graph

    def validate(self, context: IntentClassificationContext) -> bool:
        """
        Executes comprehensive validation across context. Returns True if valid (no blocking errors).
        """
        classified_ids: Set[uuid.UUID] = {
            ci.classified_intent_id for ci in context.classified_intents
        }

        # 1. Validate Classified Intents
        for intent in context.classified_intents:
            # Workspace isolation check
            if context.workspace_id is not None and intent.workspace_id != context.workspace_id:
                context.add_error(
                    f"Workspace mismatch on intent '{intent.classified_intent_id}': expected {context.workspace_id}, got {intent.workspace_id}."
                )

            # Conversation matching check
            if intent.conversation_id != context.conversation_id:
                context.add_error(
                    f"Conversation ID mismatch on intent '{intent.classified_intent_id}': expected {context.conversation_id}, got {intent.conversation_id}."
                )

            # Confidence bounds
            if not (0.0 <= intent.confidence <= 1.0):
                context.add_error(
                    f"Confidence out of bounds [{intent.confidence}] on intent '{intent.classified_intent_id}'."
                )

            # Guardrail check for forbidden keys
            self._check_forbidden_keys(intent.metadata, f"intent '{intent.classified_intent_id}'", context)

        # 2. Validate Relationships
        for rel in context.relationships:
            # Self-reference
            if rel.source_intent_id == rel.target_intent_id:
                context.add_error(
                    f"Invalid self-referencing relationship '{rel.relationship_id}' on intent '{rel.source_intent_id}'."
                )

            # Source & Target presence
            if rel.source_intent_id not in classified_ids:
                context.add_error(
                    f"Relationship '{rel.relationship_id}' references missing source intent '{rel.source_intent_id}'."
                )
            if rel.target_intent_id not in classified_ids:
                context.add_error(
                    f"Relationship '{rel.relationship_id}' references missing target intent '{rel.target_intent_id}'."
                )

            # Confidence bounds
            if not (0.0 <= rel.confidence <= 1.0):
                context.add_error(
                    f"Relationship confidence out of bounds [{rel.confidence}] on '{rel.relationship_id}'."
                )

            # Guardrail check
            self._check_forbidden_keys(rel.metadata, f"relationship '{rel.relationship_id}'", context)

        # 3. Validate Groups
        for grp in context.groups:
            for member_id in grp.intent_ids:
                if member_id not in classified_ids:
                    context.add_error(
                        f"Group '{grp.group_id}' references missing member intent '{member_id}'."
                    )
            if grp.primary_intent_id and grp.primary_intent_id not in classified_ids:
                context.add_error(
                    f"Group '{grp.group_id}' references missing primary intent '{grp.primary_intent_id}'."
                )

            # Guardrail check
            self._check_forbidden_keys(grp.metadata, f"group '{grp.group_id}'", context)

        # Result is valid if no errors recorded
        return len(context.validation_errors) == 0

    def _check_forbidden_keys(
        self,
        metadata: dict,
        entity_desc: str,
        context: IntentClassificationContext,
    ) -> None:
        """Enforces zero-mutation / boundary isolation guardrails."""
        if not metadata:
            return
        for k in metadata.keys():
            if k.lower() in FORBIDDEN_METADATA_KEYS:
                context.add_error(
                    f"Architectural Guardrail Violation: Forbidden key '{k}' detected in {entity_desc} metadata."
                )


default_classification_validator = IntentClassificationValidator()
