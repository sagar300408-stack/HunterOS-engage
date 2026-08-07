"""
HunterOS Engage V1 - Stage 1: Load Intent Artifacts
Extracts intent items, classifications, temporal histories, and conversation context into normalized raw items.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext


class Stage1_LoadIntentArtifacts:
    """
    Stage 1: Ingests IntentDetectionResult, IntentClassificationResult,
    IntentEvolutionResult, and Conversation context DTOs.
    """

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        raw_items: List[Dict[str, Any]] = []

        # 1. Ingest Detection Results
        if context.detection_result:
            intents = getattr(context.detection_result, "intents", None) or getattr(context.detection_result, "detected_intents", [])
            for det in intents:
                evidence_msgs: List[str] = []
                supp_ev = getattr(det, "supporting_evidence", None)
                if supp_ev:
                    evidence_msgs.extend(getattr(supp_ev, "source_message_ids", []))
                if not evidence_msgs and hasattr(det, "evidence_message_ids"):
                    evidence_msgs.extend(getattr(det, "evidence_message_ids", []))
                if not evidence_msgs and hasattr(det, "source_messages"):
                    evidence_msgs.extend(getattr(det, "source_messages", []))

                cat = getattr(det, "taxonomy_category", None) or getattr(det, "category", None)
                cat_str = getattr(cat, "value", str(cat)) if cat else "GENERAL"

                importance = getattr(det, "business_importance", None) or getattr(det, "importance", None)
                imp_str = getattr(importance, "value", str(importance)) if importance else "NORMAL"

                raw_items.append({
                    "intent_id": det.intent_id,
                    "canonical_name": getattr(det.intent_type, "value", str(det.intent_type)),
                    "raw_intent_type": str(det.intent_type),
                    "category": cat_str.upper(),
                    "confidence": float(det.confidence),
                    "business_importance": imp_str.upper(),
                    "evidence_message_ids": list(evidence_msgs),
                    "source_conversation": context.conversation_id,
                    "first_seen": getattr(det, "detected_at", None),
                    "last_seen": getattr(det, "detected_at", None),
                    "source_artifact": "DETECTION",
                })

        # 2. Ingest Classification Results (Enrich / add classified intents)
        if context.classification_result:
            classified_intents = getattr(context.classification_result, "classified_intents", [])
            for cls_intent in classified_intents:
                evidence_msgs = []
                supp_ev = getattr(cls_intent, "supporting_evidence", None)
                if supp_ev:
                    evidence_msgs.extend(getattr(supp_ev, "source_message_ids", []))
                if not evidence_msgs and hasattr(cls_intent, "evidence_message_ids"):
                    evidence_msgs.extend(getattr(cls_intent, "evidence_message_ids", []))

                cat = getattr(cls_intent, "business_category", None) or getattr(cls_intent, "category", None)
                cat_str = getattr(cat, "value", str(cat)) if cat else "GENERAL"

                importance = getattr(cls_intent, "business_importance", None)
                imp_str = getattr(importance, "value", str(importance)) if importance else "NORMAL"

                target_id = getattr(cls_intent, "original_intent_id", None) or getattr(cls_intent, "intent_id", uuid.uuid4())
                c_name = getattr(cls_intent, "canonical_name", None) or getattr(cls_intent, "business_process", str(target_id))

                raw_items.append({
                    "intent_id": target_id,
                    "canonical_name": c_name,
                    "raw_intent_type": c_name,
                    "category": cat_str.upper(),
                    "taxonomy_path": getattr(cls_intent, "taxonomy_path", ""),
                    "confidence": float(cls_intent.confidence),
                    "business_importance": imp_str.upper(),
                    "evidence_message_ids": list(evidence_msgs),
                    "source_conversation": context.conversation_id,
                    "source_artifact": "CLASSIFICATION",
                })

        # 3. Ingest Evolution Results (Enrich lifecycle state, velocity, timeline span)
        if context.evolution_result:
            histories = getattr(context.evolution_result, "intent_histories", [])
            for h in histories:
                lifecycle = getattr(h, "current_state", None)
                lifecycle_str = getattr(lifecycle, "value", str(lifecycle)) if lifecycle else "ACTIVE"

                velocity = getattr(h, "velocity", None)
                velocity_str = getattr(velocity, "value", str(velocity)) if velocity else "STABLE"

                raw_items.append({
                    "intent_id": h.intent_id,
                    "canonical_name": getattr(h, "canonical_name", str(h.intent_id)),
                    "lifecycle_state": lifecycle_str.upper(),
                    "velocity": velocity_str.upper(),
                    "confidence": float(getattr(h, "latest_confidence", 1.0)),
                    "source_conversation": context.conversation_id,
                    "first_seen": getattr(h, "first_seen", None),
                    "last_seen": getattr(h, "last_seen", None),
                    "source_artifact": "EVOLUTION",
                })

        context.raw_intent_items = raw_items
        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage1_LoadIntentArtifacts", duration)
