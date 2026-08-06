"""
HunterOS Engage V1 - Classification Stage 6: Group Intents
Clusters classified intents into structured functional groups.
"""

from __future__ import annotations

import time
from typing import Optional

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.grouping.engine import (
    IntentGroupingEngine,
    default_grouping_engine,
)


class GroupIntentsStage:
    """Stage 6: Groups classified intents by category and business flow."""

    def __init__(self, grouping_engine: Optional[IntentGroupingEngine] = None):
        self._engine = grouping_engine or default_grouping_engine

    def execute(self, context: IntentClassificationContext) -> None:
        start = time.perf_counter()
        context.groups = self._engine.group_intents(context)
        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage6_GroupIntents", elapsed)
