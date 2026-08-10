"""
HunterOS Engage V1 — Journey Analytics Engine
Phase 2.4.4: Analytics Configuration
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.journey.analytics.models import ResidencyCategory, TrendGranularity

@dataclass(frozen=True)
class JourneyAnalyticsConfiguration:
    version: str
    default_observation_window_days: int = 365
    default_percentile_method: str = "linear"  # numpy-compatible label
    confidence_level: float = 0.95
    minimum_probability_sample: int = 30
    enabled_metrics: List[str] = field(default_factory=list)  # empty = all enabled
    enabled_cohort_dimensions: List[str] = field(default_factory=list)
    trend_granularity: TrendGranularity = TrendGranularity.WEEKLY
    fast_residency_threshold_days: float = 3.0
    slow_residency_threshold_days: float = 14.0
    extended_residency_threshold_days: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_metric_enabled(self, metric: str) -> bool:
        if not self.enabled_metrics:
            return True  # all enabled when list is empty
        return metric in self.enabled_metrics

    def get_residency_category(self, duration_days: float) -> ResidencyCategory:
        if duration_days <= self.fast_residency_threshold_days:
            return ResidencyCategory.FAST_RESIDENCY
        elif duration_days <= self.slow_residency_threshold_days:
            return ResidencyCategory.NORMAL_RESIDENCY
        elif duration_days <= self.extended_residency_threshold_days:
            return ResidencyCategory.SLOW_RESIDENCY
        else:
            return ResidencyCategory.EXTENDED_RESIDENCY


def build_default_analytics_configuration(version: str = "analytics-v1") -> JourneyAnalyticsConfiguration:
    return JourneyAnalyticsConfiguration(
        version=version,
        default_observation_window_days=365,
        confidence_level=0.95,
        minimum_probability_sample=30,
        trend_granularity=TrendGranularity.WEEKLY,
        metadata={"description": "Default Journey Analytics Configuration"},
    )


class JourneyAnalyticsConfigurationRegistry:
    """Thread-safe versioned registry for analytics configurations."""
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._configs: Dict[str, JourneyAnalyticsConfiguration] = {}
        self._default_version: Optional[str] = None
        self._register_defaults()

    def register(self, config: JourneyAnalyticsConfiguration, set_as_default: bool = True) -> None:
        with self._lock:
            self._configs[config.version] = config
            if set_as_default or self._default_version is None:
                self._default_version = config.version

    def get(self, version: Optional[str] = None) -> Optional[JourneyAnalyticsConfiguration]:
        with self._lock:
            v = version or self._default_version
            return self._configs.get(v) if v else None

    def resolve(self, version: Optional[str] = None) -> JourneyAnalyticsConfiguration:
        with self._lock:
            cfg = self.get(version)
            return cfg if cfg is not None else build_default_analytics_configuration()

    def list(self) -> List[JourneyAnalyticsConfiguration]:
        with self._lock:
            return list(self._configs.values())

    def _register_defaults(self) -> None:
        self.register(build_default_analytics_configuration())


default_analytics_config_registry: JourneyAnalyticsConfigurationRegistry = JourneyAnalyticsConfigurationRegistry()
