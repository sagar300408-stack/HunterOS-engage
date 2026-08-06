"""
HunterOS Engage V1 - Classification Stage 2: Normalize Intent Data
Converts DetectedIntents into standard CanonicalIntents.
"""

from __future__ import annotations

import time
from typing import Optional

from app.domain.intents.classification.canonical.normalizer import (
    IntentNormalizer,
    default_intent_normalizer,
)
from app.domain.intents.classification.context import IntentClassificationContext


class NormalizeIntentDataStage:
    """Stage 2: Normalizes detected intents to CanonicalIntent models."""

    def __init__(self, normalizer: Optional[IntentNormalizer] = None):
        self._normalizer = normalizer or default_intent_normalizer

    def execute(self, context: IntentClassificationContext) -> None:
        start = time.perf_counter()
        context.canonical_intents = self._normalizer.normalize_all(context.loaded_intents)
        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage2_NormalizeIntentData", elapsed)
