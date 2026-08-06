"""
HunterOS Engage V1 - Classification Stage 1: Load Detected Intents
"""

from __future__ import annotations

import time

from app.domain.intents.classification.context import IntentClassificationContext


class LoadDetectedIntentsStage:
    """Stage 1: Ingests detected intents and upstream context."""

    def execute(self, context: IntentClassificationContext) -> None:
        start = time.perf_counter()
        if context.detection_result:
            context.loaded_intents = list(context.detection_result.intents)
        else:
            context.loaded_intents = list(context.raw_detected_intents)

        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage1_LoadDetectedIntents", elapsed)
