"""
HunterOS Engage V1 - Intent Context Validation Guardrails
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Zero-trust validator enforcing multi-tenant workspace isolation, referential integrity
between detection/classification/evolution/resolution, and strict schema compliance.
Zero predictive reasoning, zero imputation of missing data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentContextValidator:
    """
    Zero-trust validation engine for Intent Intelligence integration.
    """

    def validate_inputs(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
    ) -> List[str]:
        errors: List[str] = []

        if not conversation_id or not conversation_id.strip():
            errors.append("conversation_id cannot be empty.")
        if not entity_id or not entity_id.strip():
            errors.append("entity_id cannot be empty.")
        if not workspace_id or not workspace_id.strip():
            errors.append("workspace_id cannot be empty.")

        # 1. Multi-tenant workspace & conversation isolation checks
        if detection_result:
            if hasattr(detection_result, "conversation_id") and detection_result.conversation_id != conversation_id:
                errors.append(f"Detection Conversation ID mismatch: '{detection_result.conversation_id}' != '{conversation_id}'.")
            if hasattr(detection_result, "workspace_id") and detection_result.workspace_id and detection_result.workspace_id != workspace_id:
                errors.append(f"Detection Workspace ID mismatch: '{detection_result.workspace_id}' != '{workspace_id}'.")

        if classification_result:
            if hasattr(classification_result, "conversation_id") and classification_result.conversation_id != conversation_id:
                errors.append(f"Classification Conversation ID mismatch: '{classification_result.conversation_id}' != '{conversation_id}'.")
            if hasattr(classification_result, "workspace_id") and classification_result.workspace_id and classification_result.workspace_id != workspace_id:
                errors.append(f"Classification Workspace ID mismatch: '{classification_result.workspace_id}' != '{workspace_id}'.")

        if evolution_result:
            if hasattr(evolution_result, "conversation_id") and evolution_result.conversation_id != conversation_id:
                errors.append(f"Evolution Conversation ID mismatch: '{evolution_result.conversation_id}' != '{conversation_id}'.")
            if hasattr(evolution_result, "workspace_id") and evolution_result.workspace_id and evolution_result.workspace_id != workspace_id:
                errors.append(f"Evolution Workspace ID mismatch: '{evolution_result.workspace_id}' != '{workspace_id}'.")

        if resolution_result:
            if hasattr(resolution_result, "conversation_id") and resolution_result.conversation_id != conversation_id:
                errors.append(f"Resolution Conversation ID mismatch: '{resolution_result.conversation_id}' != '{conversation_id}'.")
            if hasattr(resolution_result, "workspace_id") and resolution_result.workspace_id and resolution_result.workspace_id != workspace_id:
                errors.append(f"Resolution Workspace ID mismatch: '{resolution_result.workspace_id}' != '{workspace_id}'.")

        return errors

    def validate_cross_subsystem_references(
        self,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
    ) -> List[str]:
        warnings: List[str] = []

        detected_ids: Set[str] = set()
        if detection_result and detection_result.detected_intents:
            detected_ids = {str(d.intent_id) for d in detection_result.detected_intents}

        # Check classification references
        if classification_result and classification_result.classified_intents and detected_ids:
            for cls in classification_result.classified_intents:
                orig_id = str(cls.original_intent_id)
                if orig_id not in detected_ids:
                    warnings.append(f"Classified intent reference '{orig_id}' not found in Detection Result.")

        # Check resolution references
        if resolution_result and resolution_result.resolution_graph and detected_ids:
            for node_id, node in resolution_result.resolution_graph.nodes.items():
                nid = str(node.intent_id)
                if nid not in detected_ids:
                    warnings.append(f"Resolution node intent '{nid}' ({node.canonical_name}) not found in Detection Result.")

        return warnings
