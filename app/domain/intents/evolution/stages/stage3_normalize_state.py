"""
HunterOS Engage V1 - Evolution Pipeline Stage 3: Normalize Intent State
Enforces deterministic canonical formats, confidence clamping, and evidence sorting.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, List

from app.domain.intents.evolution.models import IntentStateSnapshot

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class NormalizeIntentStateStage:
    """
    Stage 3: Normalizes snapshots to guarantee deterministic comparisons.
    """

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()
        normalized_snaps: List[IntentStateSnapshot] = []

        for s in context.current_snapshots:
            # Bound confidence strictly between 0.0 and 1.0
            bounded_conf = max(0.0, min(1.0, float(s.confidence)))

            # Clean and deduplicate evidence IDs
            clean_evidence = sorted(list(dict.fromkeys(str(eid).strip() for eid in s.evidence_message_ids if str(eid).strip())))

            # Clean taxonomy path
            clean_tax = s.taxonomy_path.strip() if s.taxonomy_path else "General"

            norm_s = IntentStateSnapshot(
                snapshot_id=s.snapshot_id,
                intent_id=s.intent_id,
                entity_type=s.entity_type,
                entity_id=s.entity_id.strip(),
                conversation_id=s.conversation_id.strip(),
                workspace_id=s.workspace_id,
                intent_type=s.intent_type.strip(),
                category=s.category.strip(),
                taxonomy_path=clean_tax,
                confidence=round(bounded_conf, 4),
                observed_at=s.observed_at,
                evidence_message_ids=clean_evidence,
                relationships=s.relationships,
                metadata=dict(s.metadata),
            )
            normalized_snaps.append(norm_s)

        context.current_snapshots = normalized_snaps

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage3_NormalizeIntentState", elapsed_ms)
