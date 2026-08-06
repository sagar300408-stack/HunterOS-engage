"""
HunterOS Engage V1 - Evolution Pipeline Stage 2: Load Current Snapshot
Extracts current intent states from Detection and Classification results.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import TYPE_CHECKING, List
import uuid

from app.domain.intents.evolution.models import IntentStateSnapshot

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class LoadCurrentSnapshotStage:
    """
    Stage 2: Ingests current detection and classification outputs into IntentStateSnapshots.
    """

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()
        current_snaps: List[IntentStateSnapshot] = []

        now = datetime.now(timezone.utc)

        # 1. Ingest from Canonical / Classification Result if available
        if context.classification_result and context.classification_result.classified_intents:
            for item in context.classification_result.classified_intents:
                # Find associated relationships
                rels = [
                    r.to_dict()
                    for r in context.classification_result.relationships
                    if r.source_intent_id == item.classified_id
                ]

                snap = IntentStateSnapshot(
                    intent_id=item.classified_id,
                    entity_type=context.entity_type,
                    entity_id=context.entity_id,
                    conversation_id=context.current_conversation_id,
                    workspace_id=context.workspace_id,
                    intent_type=item.canonical_intent.canonical_name,
                    category=item.canonical_intent.category.value if hasattr(item.canonical_intent.category, "value") else str(item.canonical_intent.category),
                    taxonomy_path=item.primary_taxonomy_path,
                    confidence=item.canonical_intent.confidence,
                    observed_at=now,
                    evidence_message_ids=item.canonical_intent.evidence_message_ids,
                    relationships=rels,
                    metadata={
                        "business_process": item.business_process.value if item.business_process else None,
                        "group_id": str(item.group_id) if item.group_id else None,
                        "stage": "classification",
                    },
                )
                current_snaps.append(snap)

        # 2. Fallback / supplementary ingest from Detection Result if no classified intents
        elif context.detection_result:
            det_list = getattr(context.detection_result, "intents", None) or getattr(context.detection_result, "detected_intents", [])
            for det in det_list:
                snap = IntentStateSnapshot(
                    intent_id=det.intent_id,
                    entity_type=context.entity_type,
                    entity_id=context.entity_id,
                    conversation_id=context.current_conversation_id,
                    workspace_id=context.workspace_id,
                    intent_type=det.intent_type.value if hasattr(det.intent_type, "value") else str(det.intent_type),
                    category=det.taxonomy_category.value if hasattr(det.taxonomy_category, "value") else str(det.taxonomy_category),
                    taxonomy_path=det.taxonomy_path,
                    confidence=det.confidence,
                    observed_at=det.detected_at,
                    evidence_message_ids=getattr(det, "evidence_message_ids", None) or (list(det.source_messages) if hasattr(det, "source_messages") else []),
                    relationships=[],
                    metadata={
                        "importance": det.business_importance.value if hasattr(det.business_importance, "value") else str(getattr(det, "business_importance", "")),
                        "urgency": getattr(getattr(det, "urgency", None), "value", None) or str(getattr(det, "urgency", "")),
                        "stage": "detection",
                    },
                )
                current_snaps.append(snap)

        context.current_snapshots = current_snaps

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage2_LoadCurrentSnapshot", elapsed_ms)
