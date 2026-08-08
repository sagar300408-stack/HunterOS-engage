"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Validation Framework

Validates integrity, factor bounds, sample size constraints, workspace isolation,
and calculation determinism.
"""

from __future__ import annotations

from typing import List, Optional, Union
import uuid

from app.domain.journey.exceptions import (
    JourneyValidationError,
    WorkspaceIsolationError,
)
from app.domain.journey.maturity.models import (
    JourneyMaturityResult,
    ObservedJourneyProbability,
    ObservedProbabilityStatus,
)
from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageTransition,
    JourneyState,
)


class JourneyMaturityValidator:
    """
    Validates domain constraints and data invariants for maturity calculations.
    """

    @staticmethod
    def validate_workspace_isolation(
        journey_state: JourneyState,
        workspace_id: Union[uuid.UUID, str],
    ) -> List[str]:
        """Verify that the journey belongs to the requested workspace."""
        errors: List[str] = []
        if str(journey_state.workspace_id) != str(workspace_id):
            msg = (
                f"Workspace isolation violation: journey {journey_state.journey_instance_id} "
                f"belongs to {journey_state.workspace_id}, but requested workspace is {workspace_id}."
            )
            errors.append(msg)
            raise WorkspaceIsolationError(
                expected_workspace=str(workspace_id),
                actual_workspace=str(journey_state.workspace_id),
            )
        return errors

    @staticmethod
    def validate_definition_compatibility(
        journey_state: JourneyState,
        definition: JourneyDefinition,
    ) -> List[str]:
        """Verify that the journey definition matches the state."""
        errors: List[str] = []
        stage_codes = [s.stage_code for s in definition.stages]
        if journey_state.current_stage not in stage_codes:
            errors.append(
                f"Current stage '{journey_state.current_stage.value}' not found in journey "
                f"definition '{definition.name}' ({definition.journey_type.value})."
            )
        return errors

    @staticmethod
    def validate_maturity_result(result: JourneyMaturityResult) -> List[str]:
        """
        Validate bounds and invariants of a calculated JourneyMaturityResult.
        """
        errors: List[str] = []

        # Maturity score bounds
        m_score = result.maturity.maturity_score
        if m_score < 0.0 or m_score > 1.0:
            errors.append(f"Maturity score {m_score} out of bounds [0.0, 1.0].")

        # Factor bounds
        factors = result.maturity.factors
        for name, val in [
            ("stage_position_factor", factors.stage_position_factor),
            ("stage_completion_factor", factors.stage_completion_factor),
            ("transition_history_factor", factors.transition_history_factor),
            ("evidence_strength_factor", factors.evidence_strength_factor),
            ("journey_age_factor", factors.journey_age_factor),
            ("stage_stability_factor", factors.stage_stability_factor),
            ("progression_consistency_factor", factors.progression_consistency_factor),
        ]:
            if val < 0.0 or val > 1.0:
                errors.append(f"Maturity factor '{name}'={val} out of bounds [0.0, 1.0].")

        # Momentum score bounds
        mom_score = result.momentum.momentum_score
        if mom_score < -1.0 or mom_score > 1.0:
            errors.append(f"Momentum score {mom_score} out of bounds [-1.0, 1.0].")

        # Stability score bounds
        stab_score = result.stability.stability_score
        if stab_score < 0.0 or stab_score > 1.0:
            errors.append(f"Stability score {stab_score} out of bounds [0.0, 1.0].")

        # Observed probability bounds and small-sample invariants
        if result.observed_probability is not None:
            prob = result.observed_probability
            if prob.value is not None:
                if prob.value < 0.0 or prob.value > 1.0:
                    errors.append(f"Observed probability {prob.value} out of bounds [0.0, 1.0].")
                if prob.sample_size < prob.minimum_required_sample:
                    errors.append(
                        f"Small-sample violation: probability calculated ({prob.value}) but "
                        f"sample size {prob.sample_size} < minimum required {prob.minimum_required_sample}."
                    )
            else:
                if prob.status != ObservedProbabilityStatus.INSUFFICIENT_DATA:
                    errors.append("Null probability value must have status INSUFFICIENT_DATA.")

        if errors:
            raise JourneyValidationError(
                reason="Journey maturity validation failed",
                errors=errors,
            )

        return errors


default_maturity_validator = JourneyMaturityValidator()
