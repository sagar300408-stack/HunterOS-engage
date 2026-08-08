"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Calculator

Calculates multi-factor progression maturity (0.0 - 1.0) and assigns
configurable maturity levels based on observed evidence and stage weights.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfiguration,
    default_maturity_config_registry,
)
from app.domain.journey.maturity.models import (
    JourneyMaturity,
    JourneyMaturityLevel,
    JourneyMaturityProvenance,
    MaturityFactors,
)
from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    TransitionType,
)


class JourneyMaturityCalculator:
    """
    Deterministic calculator for multi-factor Journey Maturity.
    """

    @staticmethod
    def calculate_maturity(
        journey_state: JourneyState,
        journey_definition: JourneyDefinition,
        transitions: List[JourneyStageTransition],
        config: Optional[JourneyMaturityConfiguration] = None,
        provenance: Optional[JourneyMaturityProvenance] = None,
        evaluated_at: Optional[datetime] = None,
    ) -> JourneyMaturity:
        """
        Calculate the multi-factor maturity score and level for a journey instance.
        """
        now = evaluated_at or datetime.now(timezone.utc)
        cfg = config or default_maturity_config_registry.resolve(journey_definition.journey_type)

        # 1. Stage metrics
        stages = journey_definition.stages
        total_stages = max(1, len(stages))
        stage_codes = [s.stage_code for s in stages]

        curr_stage = journey_state.current_stage
        try:
            stage_pos = stage_codes.index(curr_stage) + 1
        except ValueError:
            stage_pos = 1

        stage_progress_ratio = stage_pos / total_stages

        # 2. Stage Weights from Configuration
        stage_weight = cfg.get_stage_weight(curr_stage, default_pos=stage_progress_ratio)

        # 3. Calculate Constituent Factors
        stage_position_factor = max(0.0, min(1.0, stage_weight))

        completed_stages = set(journey_state.stage_history)
        completed_stage_count = len(completed_stages)
        stage_completion_factor = max(0.0, min(1.0, completed_stage_count / total_stages))

        # Transition History Factor
        transition_count = len(transitions)
        transition_history_factor = max(0.0, min(1.0, transition_count / max(1, total_stages - 1)))

        # Evidence Strength Factor
        if transitions:
            avg_confidence = sum(t.confidence for t in transitions) / len(transitions)
            evidence_density = min(1.0, sum(len(t.evidence) for t in transitions) / (len(transitions) * 2.0))
            evidence_strength = 0.7 * avg_confidence + 0.3 * evidence_density
        else:
            evidence_strength = 0.5
        evidence_strength_factor = max(0.0, min(1.0, evidence_strength))

        # Journey Age Factor
        journey_age_days = max(
            0.0, (now - journey_state.journey_started_at).total_seconds() / 86400.0
        )
        stage_duration_days = max(
            0.0, (now - (journey_state.stage_entered_at or journey_state.journey_started_at)).total_seconds() / 86400.0
        )
        # Healthy progression in reasonable time yields optimal factor (0.8 - 1.0)
        journey_age_factor = min(1.0, max(0.1, 1.0 - (journey_age_days / 365.0))) if journey_age_days > 0 else 0.5

        # Stage Stability & Regression History
        regressions = sum(1 for t in transitions if t.transition_type == TransitionType.REGRESSION)
        reentries = max(0, len(journey_state.stage_history) - len(set(journey_state.stage_history)))
        stability_penalty = min(0.6, (regressions * 0.2) + (reentries * 0.1))
        stage_stability_factor = max(0.0, min(1.0, 1.0 - stability_penalty))

        # Progression Consistency Factor
        advancements = sum(1 for t in transitions if t.transition_type in (TransitionType.ADVANCE, TransitionType.COMPLETION))
        total_directional = advancements + regressions
        if total_directional > 0:
            progression_consistency_factor = max(0.0, min(1.0, advancements / total_directional))
        else:
            progression_consistency_factor = 0.5

        factors = MaturityFactors(
            stage_position_factor=round(stage_position_factor, 4),
            stage_completion_factor=round(stage_completion_factor, 4),
            transition_history_factor=round(transition_history_factor, 4),
            evidence_strength_factor=round(evidence_strength_factor, 4),
            journey_age_factor=round(journey_age_factor, 4),
            stage_stability_factor=round(stage_stability_factor, 4),
            progression_consistency_factor=round(progression_consistency_factor, 4),
        )

        # 4. Weighted Score Calculation
        w = cfg.factor_weights
        total_weight = sum(w.values()) or 1.0

        raw_score = (
            w.get("stage_position", 0.30) * factors.stage_position_factor
            + w.get("stage_completion", 0.15) * factors.stage_completion_factor
            + w.get("transition_history", 0.15) * factors.transition_history_factor
            + w.get("evidence_strength", 0.20) * factors.evidence_strength_factor
            + w.get("journey_age", 0.05) * factors.journey_age_factor
            + w.get("stage_stability", 0.10) * factors.stage_stability_factor
            + w.get("progression_consistency", 0.05) * factors.progression_consistency_factor
        ) / total_weight

        # Specific terminal stage invariants
        if curr_stage == JourneyStageCode.CLOSED_WON or journey_state.status == JourneyStatus.COMPLETED:
            maturity_score = 1.0
            maturity_level = JourneyMaturityLevel.COMPLETED
        elif curr_stage in (JourneyStageCode.CLOSED_LOST, JourneyStageCode.INACTIVE) or journey_state.status in (
            JourneyStatus.LOST,
            JourneyStatus.INACTIVE,
            JourneyStatus.CANCELLED,
        ):
            maturity_score = round(max(0.0, min(0.40, raw_score)), 4)
            maturity_level = cfg.thresholds.resolve_level(maturity_score)
        elif curr_stage == JourneyStageCode.NEW_LEAD and transition_count == 0:
            maturity_score = round(max(0.0, min(0.12, raw_score)), 4)
            maturity_level = JourneyMaturityLevel.INITIAL
        else:
            maturity_score = round(max(0.0, min(1.0, raw_score)), 4)
            maturity_level = cfg.thresholds.resolve_level(maturity_score)

        # Build provenance if not provided
        prov = provenance or JourneyMaturityProvenance(
            calculation_id=uuid.uuid4(),
            journey_id=journey_state.journey_instance_id,
            workspace_id=journey_state.workspace_id or uuid.uuid4(),
            entity_id=journey_state.entity_id,
            engine_version="1.0.0",
            pipeline_version="2.4.3",
            configuration_version=cfg.version,
            generated_at=now,
            source_modules=["app.domain.journey.maturity.calculators.maturity"],
            source_artifacts=[f"journey_state:{journey_state.journey_instance_id}"],
            calculation_method="MULTI_FACTOR_WEIGHTED_DETERMINISTIC",
        )

        return JourneyMaturity(
            maturity_score=maturity_score,
            maturity_level=maturity_level,
            current_stage=curr_stage,
            stage_position=stage_pos,
            total_active_stages=total_stages,
            completed_stage_count=completed_stage_count,
            journey_progress_ratio=round(stage_progress_ratio, 4),
            stage_duration_days=round(stage_duration_days, 4),
            journey_age_days=round(journey_age_days, 4),
            evidence_strength=round(evidence_strength, 4),
            calculated_at=now,
            factors=factors,
            provenance=prov,
        )


default_maturity_calculator = JourneyMaturityCalculator()
