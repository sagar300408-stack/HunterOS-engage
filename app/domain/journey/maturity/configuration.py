"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Configuration & Registry

Configurable maturity models, stage weights, factor weights, and score thresholds
supporting Cross-Industry, Real Estate, Healthcare, Service, and Custom domains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Any, Dict, List, Optional, Union

from app.domain.journey.maturity.models import (
    JourneyMaturityLevel,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyType,
)


@dataclass(frozen=True)
class MaturityScoreThresholds:
    """Configurable score boundaries mapping numeric maturity (0.0-1.0) to JourneyMaturityLevel."""
    initial_max: float = 0.15
    early_max: float = 0.30
    developing_max: float = 0.50
    qualified_max: float = 0.65
    advanced_max: float = 0.80
    late_stage_max: float = 0.95

    def resolve_level(self, score: float) -> JourneyMaturityLevel:
        """Deterministically map a 0.0-1.0 maturity score to its corresponding level."""
        score = max(0.0, min(1.0, float(score)))
        if score < self.initial_max:
            return JourneyMaturityLevel.INITIAL
        elif score < self.early_max:
            return JourneyMaturityLevel.EARLY
        elif score < self.developing_max:
            return JourneyMaturityLevel.DEVELOPING
        elif score < self.qualified_max:
            return JourneyMaturityLevel.QUALIFIED
        elif score < self.advanced_max:
            return JourneyMaturityLevel.ADVANCED
        elif score < self.late_stage_max:
            return JourneyMaturityLevel.LATE_STAGE
        else:
            return JourneyMaturityLevel.COMPLETED


@dataclass(frozen=True)
class JourneyMaturityConfiguration:
    """
    Configuration specification for journey maturity scoring and observed probabilities.
    """
    journey_type: JourneyType
    version: str
    factor_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "stage_position": 0.30,
            "stage_completion": 0.15,
            "transition_history": 0.15,
            "evidence_strength": 0.20,
            "journey_age": 0.05,
            "stage_stability": 0.10,
            "progression_consistency": 0.05,
        }
    )
    stage_weights: Dict[JourneyStageCode, float] = field(default_factory=dict)
    thresholds: MaturityScoreThresholds = field(default_factory=MaturityScoreThresholds)
    minimum_evidence_required: int = 1
    minimum_transition_count: int = 0
    minimum_sample_for_probability: int = 30
    observation_window_days: int = 365
    configuration_metadata: Dict[str, Any] = field(default_factory=dict)

    def get_stage_weight(self, stage: JourneyStageCode, default_pos: float = 0.0) -> float:
        """Retrieve the configured stage weight or fall back to position-based default."""
        return self.stage_weights.get(stage, default_pos)


# ── Built-in Standard Configurations ─────────────────────────────────────────


def build_sales_maturity_configuration(version: str = "sales-v1") -> JourneyMaturityConfiguration:
    """Cross-Industry standard Sales maturity configuration."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.05,
        JourneyStageCode.INTERESTED: 0.20,
        JourneyStageCode.QUALIFIED: 0.40,
        JourneyStageCode.ENGAGED: 0.50,
        JourneyStageCode.MEETING_SCHEDULED: 0.60,
        JourneyStageCode.MEETING_COMPLETED: 0.70,
        JourneyStageCode.PROPOSAL: 0.80,
        JourneyStageCode.NEGOTIATION: 0.90,
        JourneyStageCode.BOOKING: 0.95,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.SALES,
        version=version,
        stage_weights=stage_weights,
        minimum_sample_for_probability=30,
        configuration_metadata={"description": "Standard Cross-Industry Sales Maturity Model"},
    )


def build_real_estate_maturity_configuration(
    version: str = "real-estate-v1",
) -> JourneyMaturityConfiguration:
    """First-class Real Estate Property Purchase & Rental maturity configuration."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.05,
        JourneyStageCode.INTERESTED: 0.15,
        JourneyStageCode.QUALIFIED: 0.30,
        JourneyStageCode.SITE_VISIT_SCHEDULED: 0.45,
        JourneyStageCode.SITE_VISIT_COMPLETED: 0.60,
        JourneyStageCode.PROPERTY_SHORTLISTED: 0.70,
        JourneyStageCode.NEGOTIATION: 0.85,
        JourneyStageCode.BOOKING: 0.95,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.PROPERTY_PURCHASE,
        version=version,
        stage_weights=stage_weights,
        minimum_sample_for_probability=25,
        configuration_metadata={"description": "Real Estate Property Purchase Maturity Model", "industry": "REAL_ESTATE"},
    )


def build_real_estate_rental_maturity_configuration(
    version: str = "real-estate-rental-v1",
) -> JourneyMaturityConfiguration:
    """Real Estate Property Rental maturity configuration."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.05,
        JourneyStageCode.INTERESTED: 0.20,
        JourneyStageCode.QUALIFIED: 0.35,
        JourneyStageCode.SITE_VISIT_SCHEDULED: 0.50,
        JourneyStageCode.SITE_VISIT_COMPLETED: 0.65,
        JourneyStageCode.PROPERTY_SHORTLISTED: 0.75,
        JourneyStageCode.NEGOTIATION: 0.85,
        JourneyStageCode.BOOKING: 0.95,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.PROPERTY_RENTAL,
        version=version,
        stage_weights=stage_weights,
        minimum_sample_for_probability=20,
        configuration_metadata={"description": "Real Estate Property Rental Maturity Model", "industry": "REAL_ESTATE"},
    )


def build_service_maturity_configuration(version: str = "service-v1") -> JourneyMaturityConfiguration:
    """Standard Service lifecycle maturity configuration."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.10,
        JourneyStageCode.QUALIFIED: 0.35,
        JourneyStageCode.ENGAGED: 0.60,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.SERVICE,
        version=version,
        stage_weights=stage_weights,
        configuration_metadata={"description": "Standard Service Lifecycle Maturity Model"},
    )


def build_support_maturity_configuration(version: str = "support-v1") -> JourneyMaturityConfiguration:
    """Standard Support lifecycle maturity configuration."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.10,
        JourneyStageCode.ENGAGED: 0.50,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.SUPPORT,
        version=version,
        stage_weights=stage_weights,
        configuration_metadata={"description": "Standard Support Lifecycle Maturity Model"},
    )


def build_healthcare_maturity_configuration(version: str = "healthcare-v1") -> JourneyMaturityConfiguration:
    """Healthcare lifecycle maturity configuration stub."""
    stage_weights = {
        JourneyStageCode.NEW_LEAD: 0.10,
        JourneyStageCode.CONSULTATION_SCHEDULED: 0.40,
        JourneyStageCode.CONSULTATION_COMPLETED: 0.70,
        JourneyStageCode.TREATMENT_PLAN: 0.90,
        JourneyStageCode.CLOSED_WON: 1.00,
        JourneyStageCode.CLOSED_LOST: 0.00,
        JourneyStageCode.INACTIVE: 0.00,
    }
    return JourneyMaturityConfiguration(
        journey_type=JourneyType.HEALTHCARE,
        version=version,
        stage_weights=stage_weights,
        minimum_sample_for_probability=30,
        configuration_metadata={"description": "Healthcare Lifecycle Maturity Model", "industry": "HEALTHCARE"},
    )


# ── Configuration Registry ───────────────────────────────────────────────────


class JourneyMaturityConfigurationRegistry:
    """
    Thread-safe registry for versioned JourneyMaturityConfigurations.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._configs: Dict[str, JourneyMaturityConfiguration] = {}
        self._default_by_type: Dict[JourneyType, str] = {}
        self._register_defaults()

    def _make_key(self, journey_type: JourneyType, version: str) -> str:
        return f"{journey_type.value}::{version}"

    def register(self, config: JourneyMaturityConfiguration, set_as_default: bool = True) -> None:
        """Register a maturity configuration."""
        with self._lock:
            key = self._make_key(config.journey_type, config.version)
            self._configs[key] = config
            if set_as_default or config.journey_type not in self._default_by_type:
                self._default_by_type[config.journey_type] = config.version

    def get(self, journey_type: JourneyType, version: Optional[str] = None) -> Optional[JourneyMaturityConfiguration]:
        """Retrieve a configuration by journey type and version."""
        with self._lock:
            if version is None:
                version = self._default_by_type.get(journey_type)
            if version is None:
                return None
            return self._configs.get(self._make_key(journey_type, version))

    def resolve(self, journey_type: JourneyType, version: Optional[str] = None) -> JourneyMaturityConfiguration:
        """Resolve a configuration or fall back to standard sales maturity configuration."""
        with self._lock:
            cfg = self.get(journey_type, version)
            if cfg is not None:
                return cfg
            # Fallback to default sales configuration
            return self._configs.get(self._make_key(JourneyType.SALES, "sales-v1")) or build_sales_maturity_configuration()

    def list(self) -> List[JourneyMaturityConfiguration]:
        """List all registered maturity configurations."""
        with self._lock:
            return list(self._configs.values())

    def _register_defaults(self) -> None:
        """Register all default configurations."""
        self.register(build_sales_maturity_configuration())
        self.register(build_real_estate_maturity_configuration())
        self.register(build_real_estate_rental_maturity_configuration())
        self.register(build_service_maturity_configuration())
        self.register(build_support_maturity_configuration())
        self.register(build_healthcare_maturity_configuration())


default_maturity_config_registry: JourneyMaturityConfigurationRegistry = (
    JourneyMaturityConfigurationRegistry()
)
