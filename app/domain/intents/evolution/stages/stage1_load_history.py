"""
HunterOS Engage V1 - Evolution Pipeline Stage 1: Load Historical Snapshots
Loads historical snapshots and prior event stream for the subject entity.
"""

from __future__ import annotations

import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext
    from app.domain.intents.evolution.repository import IntentEvolutionRepository


class LoadHistoricalSnapshotsStage:
    """
    Stage 1: Ingests prior historical snapshots and event stream for entity.
    """

    def __init__(self, repository: Optional[IntentEvolutionRepository] = None):
        self.repository = repository

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()

        if self.repository:
            # Fetch historical stream & snapshots from repository
            stream = self.repository.get_event_stream(
                entity_id=context.entity_id,
                entity_type=context.entity_type,
                workspace_id=context.workspace_id,
            )
            if stream:
                context.historical_stream = stream
                context.updated_stream = stream

            snapshots = self.repository.get_snapshots(
                entity_id=context.entity_id,
                entity_type=context.entity_type,
                workspace_id=context.workspace_id,
            )
            context.historical_snapshots = snapshots

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage1_LoadHistoricalSnapshots", elapsed_ms)
