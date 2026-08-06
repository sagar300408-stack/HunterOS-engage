"""
HunterOS Engage V1 - Evolution Pipeline Stage 4: Compare Snapshots
Generates detailed differential records between historical and current intent snapshots.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Set
import uuid

from app.domain.intents.evolution.models import IntentStateSnapshot

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class CompareSnapshotsStage:
    """
    Stage 4: Computes semantic, confidence, and taxonomy differentials across snapshots.
    """

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()
        diffs: List[Dict[str, Any]] = []

        hist_by_path: Dict[str, IntentStateSnapshot] = {
            h.taxonomy_path: h for h in context.historical_snapshots
        }
        hist_by_id: Dict[uuid.UUID, IntentStateSnapshot] = {
            h.intent_id: h for h in context.historical_snapshots
        }

        matched_hist_paths: Set[str] = set()

        for curr in context.current_snapshots:
            hist_match = hist_by_path.get(curr.taxonomy_path) or hist_by_id.get(curr.intent_id)

            if hist_match:
                matched_hist_paths.add(hist_match.taxonomy_path)
                conf_delta = round(curr.confidence - hist_match.confidence, 4)
                diff = {
                    "intent_id": str(curr.intent_id),
                    "taxonomy_path": curr.taxonomy_path,
                    "change_type": "PERSISTING",
                    "previous_confidence": hist_match.confidence,
                    "current_confidence": curr.confidence,
                    "confidence_delta": conf_delta,
                    "category_changed": curr.category != hist_match.category,
                    "previous_snapshot_id": str(hist_match.snapshot_id),
                    "current_snapshot_id": str(curr.snapshot_id),
                }
            else:
                diff = {
                    "intent_id": str(curr.intent_id),
                    "taxonomy_path": curr.taxonomy_path,
                    "change_type": "EMERGED",
                    "previous_confidence": None,
                    "current_confidence": curr.confidence,
                    "confidence_delta": 0.0,
                    "category_changed": False,
                    "previous_snapshot_id": None,
                    "current_snapshot_id": str(curr.snapshot_id),
                }
            diffs.append(diff)

        # Check for disappearing historical intents
        for h_path, h_snap in hist_by_path.items():
            if h_path not in matched_hist_paths:
                diffs.append({
                    "intent_id": str(h_snap.intent_id),
                    "taxonomy_path": h_path,
                    "change_type": "ABSENT_IN_CURRENT",
                    "previous_confidence": h_snap.confidence,
                    "current_confidence": 0.0,
                    "confidence_delta": -h_snap.confidence,
                    "category_changed": False,
                    "previous_snapshot_id": str(h_snap.snapshot_id),
                    "current_snapshot_id": None,
                })

        context.snapshot_diffs = diffs

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage4_CompareSnapshots", elapsed_ms)
