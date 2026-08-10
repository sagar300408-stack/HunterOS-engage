"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Analytics Validator

Non-raising validation. Collects warnings and errors.
Never silently repairs invalid data.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Union

from app.domain.journey.models import JourneyState, JourneyStageTransition
from app.domain.journey.analytics.models import AnalyticsObservationWindow, JourneyAnalyticsResult
from app.domain.journey.analytics.context import JourneyAnalyticsContext

class JourneyAnalyticsValidator:
    """
    Validates analytics context and results.
    Returns lists of warnings/errors; never raises.
    """

    def validate_workspace_isolation(
        self, journeys: List[JourneyState], workspace_id: Union[uuid.UUID, str]
    ) -> List[str]:
        """Verify all journeys belong to the same workspace."""
        errors = []
        ws = str(workspace_id)
        for j in journeys:
            if str(j.workspace_id) != ws:
                errors.append(
                    f"Workspace isolation violation: journey {j.journey_instance_id} "
                    f"belongs to workspace {j.workspace_id}, expected {ws}."
                )
        return errors

    def validate_observation_window(
        self, window: AnalyticsObservationWindow
    ) -> List[str]:
        warnings = []
        if window.start_at >= window.end_at:
            warnings.append("Observation window start_at must be before end_at.")
        if window.duration_days > 3650:
            warnings.append("Observation window exceeds 10 years; analytics may be very large.")
        return warnings

    def validate_duplicate_journeys(
        self, journeys: List[JourneyState]
    ) -> List[str]:
        seen = set()
        dupes = []
        for j in journeys:
            jid = str(j.journey_instance_id)
            if jid in seen:
                dupes.append(f"Duplicate journey detected: {jid}")
            seen.add(jid)
        return dupes

    def validate_duplicate_transitions(
        self, transitions: List[JourneyStageTransition]
    ) -> List[str]:
        seen = set()
        dupes = []
        for t in transitions:
            tid = str(t.transition_id)
            if tid in seen:
                dupes.append(f"Duplicate transition detected: {tid}")
            seen.add(tid)
        return dupes

    def validate_percentage_bounds(
        self, percentages: Dict[str, float], context: str = ""
    ) -> List[str]:
        warnings = []
        total = sum(percentages.values())
        if percentages and abs(total - 100.0) > 0.1:
            warnings.append(
                f"Percentage sum {total:.2f}% deviates from 100% in {context}"
            )
        return warnings

    def validate_probability_bounds(
        self, value: Optional[float], label: str = ""
    ) -> List[str]:
        if value is None:
            return []
        if not (0.0 <= value <= 1.0):
            return [f"Probability {label}={value} is outside [0,1] bounds."]
        return []

    def validate_analytics_context(
        self, context: JourneyAnalyticsContext
    ) -> List[str]:
        errors: List[str] = []
        errors.extend(self.validate_workspace_isolation(context.journey_states, context.workspace_id))
        errors.extend(self.validate_observation_window(context.observation_window))
        errors.extend(self.validate_duplicate_journeys(context.journey_states))
        errors.extend(self.validate_duplicate_transitions(context.transitions))
        return errors

    def validate_analytics_result(
        self, result: JourneyAnalyticsResult
    ) -> List[str]:
        warnings: List[str] = []
        # Check distribution percentages sum to ~100 or 0 (if empty)
        if result.journey_count > 0:
            warnings.extend(
                self.validate_percentage_bounds(
                    result.distribution.by_status, "status distribution"
                )
            )
        return warnings


default_analytics_validator: JourneyAnalyticsValidator = JourneyAnalyticsValidator()
