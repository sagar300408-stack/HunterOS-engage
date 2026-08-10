"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Confidence Interval Engine

Reuses Wilson Score methodology from Phase 2.4.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.journey.maturity.probability import calculate_wilson_score_interval


@dataclass(frozen=True)
class ConfidenceInterval:
    sample_size: int
    success_count: int
    confidence_level: float
    point_estimate: float
    lower_bound: float
    upper_bound: float
    method: str = "WILSON_SCORE_INTERVAL"
    satisfied_minimum_sample: bool = True


def calculate_proportion_ci(
    successes: int,
    sample_size: int,
    confidence_level: float = 0.95,
    minimum_sample: int = 30,
) -> ConfidenceInterval:
    """Calculate Wilson confidence interval for a proportion."""
    satisfied = sample_size >= minimum_sample
    if sample_size <= 0:
        return ConfidenceInterval(
            sample_size=0, success_count=0, confidence_level=confidence_level,
            point_estimate=0.0, lower_bound=0.0, upper_bound=0.0,
            satisfied_minimum_sample=False,
        )
    p, lower, upper = calculate_wilson_score_interval(successes, sample_size, confidence_level)
    return ConfidenceInterval(
        sample_size=sample_size,
        success_count=successes,
        confidence_level=confidence_level,
        point_estimate=round(p, 4),
        lower_bound=round(lower, 4),
        upper_bound=round(upper, 4),
        satisfied_minimum_sample=satisfied,
    )
