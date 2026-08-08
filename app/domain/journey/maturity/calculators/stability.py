"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Stability Calculator

Evaluates journey state stability, detecting re-entry oscillation, regression cycles,
and evidence consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.domain.journey.maturity.models import (
    JourneyStability,
    JourneyStabilityLevel,
)
from app.domain.journey.models import (
    JourneyStageTransition,
    JourneyState,
    TransitionType,
)


class JourneyStabilityCalculator:
    """
    Evaluates evidence-backed stability and oscillation of a customer journey.
    """

    @staticmethod
    def calculate_stability(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        evaluated_at: Optional[datetime] = None,
    ) -> JourneyStability:
        """
        Calculate descriptive stability metrics.
        """
        now = evaluated_at or datetime.now(timezone.utc)
        curr_entered_at = journey_state.stage_entered_at or journey_state.journey_started_at
        current_stage_duration_days = max(
            0.0, (now - curr_entered_at).total_seconds() / 86400.0
        )

        # 1. Count re-entries in stage history
        history = list(journey_state.stage_history)
        unique_stages = set(history)
        stage_reentry_count = max(0, len(history) - len(unique_stages))

        # 2. Count regressions
        regressions = sum(
            1 for t in transitions if t.transition_type == TransitionType.REGRESSION
        )

        # 3. Count supporting vs conflicting evidence
        supporting_evidence_count = 0
        conflicting_evidence_count = 0

        for t in transitions:
            for ev in t.evidence:
                desc_lower = ev.description.lower()
                if "conflict" in desc_lower or "reject" in desc_lower or "cancel" in desc_lower:
                    conflicting_evidence_count += 1
                else:
                    supporting_evidence_count += 1

        # 4. Compute stability score (0.0 - 1.0)
        base_score = 0.90
        # If no transitions and young journey -> very stable baseline
        if not transitions and current_stage_duration_days <= 14:
            base_score = 0.95

        # Penalties
        reentry_penalty = min(0.40, stage_reentry_count * 0.15)
        regression_penalty = min(0.40, regressions * 0.20)
        conflict_penalty = min(0.30, conflicting_evidence_count * 0.10)

        # Boost for solid duration with supporting evidence
        evidence_boost = min(0.15, supporting_evidence_count * 0.02)

        raw_score = base_score - reentry_penalty - regression_penalty - conflict_penalty + evidence_boost
        stability_score = round(max(0.05, min(1.0, raw_score)), 4)

        # 5. Determine stability level
        if stability_score >= 0.85:
            level = JourneyStabilityLevel.VERY_STABLE
        elif stability_score >= 0.65:
            level = JourneyStabilityLevel.STABLE
        elif stability_score >= 0.45:
            level = JourneyStabilityLevel.MODERATE
        elif stability_score >= 0.25:
            level = JourneyStabilityLevel.UNSTABLE
        else:
            level = JourneyStabilityLevel.HIGHLY_UNSTABLE

        factors: Dict[str, float] = {
            "base_score": base_score,
            "reentry_penalty": reentry_penalty,
            "regression_penalty": regression_penalty,
            "conflict_penalty": conflict_penalty,
            "evidence_boost": evidence_boost,
            "current_duration_factor": min(1.0, current_stage_duration_days / 30.0),
        }

        return JourneyStability(
            stability_score=stability_score,
            stability_level=level,
            current_stage_duration_days=round(current_stage_duration_days, 2),
            stage_reentry_count=stage_reentry_count,
            stage_transition_count=len(transitions),
            supporting_evidence_count=supporting_evidence_count,
            conflicting_evidence_count=conflicting_evidence_count,
            calculated_at=now,
            factors=factors,
        )


default_stability_calculator = JourneyStabilityCalculator()
