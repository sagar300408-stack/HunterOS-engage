"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Stage Residency Calculator

Calculates immutable historical stage residency intervals and tracks current open residency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid

from app.domain.journey.maturity.models import (
    StageResidency,
    StageResidencyStatus,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
)


class StageResidencyCalculator:
    """
    Constructs chronological StageResidency records from journey state and transitions.
    """

    @staticmethod
    def calculate_residency(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        evaluated_at: Optional[datetime] = None,
    ) -> Tuple[List[StageResidency], StageResidency]:
        """
        Reconstruct all closed residency intervals plus the active residency interval.
        Returns: (all_residencies, current_active_residency).
        """
        now = evaluated_at or datetime.now(timezone.utc)
        sorted_transitions = sorted(transitions, key=lambda t: t.occurred_at)

        residencies: List[StageResidency] = []
        stage_counts: dict[JourneyStageCode, int] = {}

        # 1. Reconstruct historical closed residencies
        if sorted_transitions:
            first_t = sorted_transitions[0]
            # Initial stage prior to first transition
            initial_stage = first_t.from_stage or journey_state.stage_history[0] if journey_state.stage_history else journey_state.current_stage
            prev_stage = initial_stage
            prev_entered_at = journey_state.journey_started_at

            stage_counts[prev_stage] = stage_counts.get(prev_stage, 0) + 1
            reentry = stage_counts[prev_stage] - 1

            for t in sorted_transitions:
                duration_days = max(
                    0.0, (t.occurred_at - prev_entered_at).total_seconds() / 86400.0
                )
                residency = StageResidency(
                    residency_id=uuid.uuid4(),
                    stage=prev_stage,
                    entered_at=prev_entered_at,
                    exited_at=t.occurred_at,
                    duration_days=round(duration_days, 4),
                    transition_count=1,
                    reentry_count=reentry,
                    evidence_count=len(t.evidence),
                    confidence=t.confidence,
                    status=StageResidencyStatus.COMPLETED,
                )
                residencies.append(residency)

                # Advance to next stage
                prev_stage = t.to_stage
                prev_entered_at = t.occurred_at
                stage_counts[prev_stage] = stage_counts.get(prev_stage, 0) + 1
                reentry = stage_counts[prev_stage] - 1

        # 2. Construct the current active residency
        curr_stage = journey_state.current_stage
        curr_entered_at = journey_state.stage_entered_at or journey_state.journey_started_at
        current_reentry = max(0, stage_counts.get(curr_stage, 1) - 1)
        current_duration_days = max(
            0.0, (now - curr_entered_at).total_seconds() / 86400.0
        )

        active_residency = StageResidency(
            residency_id=uuid.uuid4(),
            stage=curr_stage,
            entered_at=curr_entered_at,
            exited_at=None,
            duration_days=round(current_duration_days, 4),
            transition_count=len(sorted_transitions),
            reentry_count=current_reentry,
            evidence_count=sum(len(t.evidence) for t in sorted_transitions),
            confidence=1.0,
            status=StageResidencyStatus.ACTIVE,
        )
        residencies.append(active_residency)

        return residencies, active_residency


default_residency_calculator = StageResidencyCalculator()
