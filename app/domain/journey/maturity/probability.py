"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Observed Probability Calculator

Statistical, purely descriptive historical outcome likelihood calculator.
Strictly calculates historical observed frequencies from closed historical journeys
belonging to the exact same workspace.

CRITICAL INVARIANTS:
1. STRICTLY HISTORICAL & DESCRIPTIVE: Never predicts future actions or guarantees conversion.
2. NO SMALL-SAMPLE FICTION: If sample size < minimum_sample, value is None with status INSUFFICIENT_DATA.
3. WORKSPACE ISOLATION: Cross-workspace historical aggregation is strictly forbidden.
4. WILSON SCORE INTERVAL: Uses deterministic binomial proportion confidence intervals.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.maturity.models import (
    JourneyMaturityProvenance,
    ObservedJourneyProbability,
    ObservedProbabilityStatus,
    ObservedProbabilityType,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
    JourneyType,
)


def calculate_wilson_score_interval(
    successes: int,
    sample_size: int,
    confidence_level: float = 0.95,
) -> tuple[float, float, float]:
    """
    Calculate the Wilson score interval for a binomial proportion.
    Returns: (point_estimate, lower_bound, upper_bound).
    """
    if sample_size <= 0:
        return 0.0, 0.0, 0.0

    # Z-value mapping for standard confidence levels
    z_map = {
        0.90: 1.644853,
        0.95: 1.959964,
        0.99: 2.575829,
    }
    z = z_map.get(round(confidence_level, 2), 1.959964)

    p = successes / sample_size
    n = sample_size

    denominator = 1.0 + (z * z) / n
    center = (p + (z * z) / (2.0 * n)) / denominator
    spread = (
        z * math.sqrt((p * (1.0 - p) / n) + ((z * z) / (4.0 * n * n)))
    ) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return p, lower, upper


class ObservedProbabilityCalculator:
    """
    Descriptive statistical calculator for observed historical journey probabilities.
    Calculates empirical conversion rates from historical closed journey cohorts.
    """

    def __init__(self, default_min_sample: int = 30) -> None:
        self.default_min_sample = default_min_sample

    def calculate_from_historical_cohort(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: JourneyType,
        current_stage: JourneyStageCode,
        historical_journeys: List[JourneyState],
        target_outcome: str = "CLOSED_WON",
        minimum_required_sample: Optional[int] = None,
        observation_window_days: int = 365,
        confidence_level: float = 0.95,
        cohort_filters: Optional[Dict[str, Any]] = None,
        provenance: Optional[JourneyMaturityProvenance] = None,
    ) -> ObservedJourneyProbability:
        """
        Calculate observed historical probability from a list of completed historical journeys.
        """
        min_sample = minimum_required_sample if minimum_required_sample is not None else self.default_min_sample
        ws_str = str(workspace_id)
        cohort_dict = cohort_filters or {}
        limitations: List[str] = []

        # 1. Filter historical journeys strictly within the workspace
        eligible_journeys: List[JourneyState] = []
        for j in historical_journeys:
            # Workspace isolation invariant
            if str(j.workspace_id) != ws_str:
                continue

            # Must have reached or passed the current stage in its stage history
            reached_stage = (
                current_stage in j.stage_history or j.current_stage == current_stage
            )
            if not reached_stage:
                continue

            # Must be a completed/terminal journey (CLOSED_WON or CLOSED_LOST)
            is_terminal = (
                j.status in (JourneyStatus.COMPLETED, JourneyStatus.LOST, JourneyStatus.INACTIVE, JourneyStatus.CANCELLED)
                or j.current_stage in (
                    JourneyStageCode.CLOSED_WON,
                    JourneyStageCode.CLOSED_LOST,
                    JourneyStageCode.INACTIVE,
                )
            )
            if not is_terminal:
                continue

            # Check cohort filters if specified
            matches_cohort = True
            for k, v in cohort_dict.items():
                if k == "journey_type" and j.metadata.get("journey_type") != v:
                    matches_cohort = False
                    break
                elif k == "property_type" and j.metadata.get("property_type") != v:
                    matches_cohort = False
                    break
                elif k == "source_channel" and j.metadata.get("source_channel") != v:
                    matches_cohort = False
                    break

            if matches_cohort:
                eligible_journeys.append(j)

        sample_size = len(eligible_journeys)

        # 2. Check for small sample size
        if sample_size < min_sample:
            limitations.append(
                f"Insufficient historical sample size: observed {sample_size} journeys, "
                f"minimum required is {min_sample}."
            )
            return ObservedJourneyProbability(
                probability_id=uuid.uuid4(),
                value=None,
                status=ObservedProbabilityStatus.INSUFFICIENT_DATA,
                probability_type=ObservedProbabilityType.HISTORICAL_OBSERVED,
                target_stage=JourneyStageCode.CLOSED_WON if target_outcome == "CLOSED_WON" else None,
                target_outcome=target_outcome,
                sample_size=sample_size,
                success_count=0,
                failure_count=0,
                minimum_required_sample=min_sample,
                minimum_sample_met=False,
                observation_window_days=observation_window_days,
                calculation_method="WILSON_SCORE_INTERVAL",
                confidence=0.0,
                confidence_interval_lower=None,
                confidence_interval_upper=None,
                confidence_level=confidence_level,
                cohort_filters=cohort_dict,
                limitations=limitations,
                provenance=provenance,
                calculated_at=datetime.now(timezone.utc),
            )

        # 3. Count successes and failures
        success_count = 0
        failure_count = 0

        for j in eligible_journeys:
            if j.current_stage == JourneyStageCode.CLOSED_WON or j.status == JourneyStatus.COMPLETED:
                success_count += 1
            else:
                failure_count += 1

        # 4. Calculate Wilson score interval
        p, lower, upper = calculate_wilson_score_interval(
            successes=success_count,
            sample_size=sample_size,
            confidence_level=confidence_level,
        )

        limitations.append(
            f"Descriptive historical probability based on {sample_size} completed journeys "
            f"reaching stage '{current_stage.value}' within workspace {ws_str}."
        )

        return ObservedJourneyProbability(
            probability_id=uuid.uuid4(),
            value=round(p, 4),
            status=ObservedProbabilityStatus.CALCULATED,
            probability_type=ObservedProbabilityType.HISTORICAL_OBSERVED,
            target_stage=JourneyStageCode.CLOSED_WON if target_outcome == "CLOSED_WON" else None,
            target_outcome=target_outcome,
            sample_size=sample_size,
            success_count=success_count,
            failure_count=failure_count,
            minimum_required_sample=min_sample,
            minimum_sample_met=True,
            observation_window_days=observation_window_days,
            calculation_method="WILSON_SCORE_INTERVAL",
            confidence=round(1.0 - (upper - lower), 4) if upper >= lower else 0.5,
            confidence_interval_lower=round(lower, 4),
            confidence_interval_upper=round(upper, 4),
            confidence_level=confidence_level,
            cohort_filters=cohort_dict,
            limitations=limitations,
            provenance=provenance,
            calculated_at=datetime.now(timezone.utc),
        )


default_probability_calculator: ObservedProbabilityCalculator = (
    ObservedProbabilityCalculator()
)
