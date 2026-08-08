"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity & Observed Probability Module

Descriptive journey intelligence layer evaluating journey maturity, momentum, stability,
residency, velocity, observed probability, and health.
"""

from app.domain.journey.maturity.calculators.health import (
    JourneyHealthCalculator,
    default_health_calculator,
)
from app.domain.journey.maturity.calculators.maturity import (
    JourneyMaturityCalculator,
    default_maturity_calculator,
)
from app.domain.journey.maturity.calculators.momentum import (
    JourneyMomentumCalculator,
    default_momentum_calculator,
)
from app.domain.journey.maturity.calculators.residency import (
    StageResidencyCalculator,
    default_residency_calculator,
)
from app.domain.journey.maturity.calculators.stability import (
    JourneyStabilityCalculator,
    default_stability_calculator,
)
from app.domain.journey.maturity.calculators.velocity import (
    StageVelocityCalculator,
    default_velocity_calculator,
)
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfiguration,
    JourneyMaturityConfigurationRegistry,
    MaturityScoreThresholds,
    build_healthcare_maturity_configuration,
    build_real_estate_maturity_configuration,
    build_real_estate_rental_maturity_configuration,
    build_sales_maturity_configuration,
    build_service_maturity_configuration,
    build_support_maturity_configuration,
    default_maturity_config_registry,
)
from app.domain.journey.maturity.engine import (
    JourneyMaturityEngine,
    default_maturity_engine,
)
from app.domain.journey.maturity.models import (
    JourneyHealth,
    JourneyHealthState,
    JourneyMaturity,
    JourneyMaturityDiagnostics,
    JourneyMaturityLevel,
    JourneyMaturityProvenance,
    JourneyMaturityResult,
    JourneyMomentum,
    JourneyMomentumState,
    JourneyStability,
    JourneyStabilityLevel,
    MaturityFactors,
    ObservedJourneyProbability,
    ObservedProbability,
    ObservedProbabilityStatus,
    ObservedProbabilityType,
    StageResidency,
    StageResidencyStatus,
    StageVelocity,
    StageVelocityState,
)
from app.domain.journey.maturity.probability import (
    ObservedProbabilityCalculator,
    calculate_wilson_score_interval,
    default_probability_calculator,
)
from app.domain.journey.maturity.query import (
    JourneyMaturityQueryEngine,
    default_maturity_query_engine,
)
from app.domain.journey.maturity.repository import (
    InMemoryJourneyMaturityRepository,
    JourneyMaturityReadRepository,
    JourneyMaturityWriteRepository,
    default_maturity_repository,
)
from app.domain.journey.maturity.validation import (
    JourneyMaturityValidator,
    default_maturity_validator,
)

__all__ = [
    # Enums
    "JourneyMaturityLevel",
    "JourneyMomentumState",
    "JourneyStabilityLevel",
    "StageResidencyStatus",
    "StageVelocityState",
    "ObservedProbabilityType",
    "ObservedProbabilityStatus",
    "JourneyHealthState",
    # Models
    "MaturityFactors",
    "JourneyMaturity",
    "JourneyMomentum",
    "JourneyStability",
    "StageResidency",
    "StageVelocity",
    "ObservedJourneyProbability",
    "ObservedProbability",
    "JourneyHealth",
    "JourneyMaturityDiagnostics",
    "JourneyMaturityProvenance",
    "JourneyMaturityResult",
    # Configuration
    "MaturityScoreThresholds",
    "JourneyMaturityConfiguration",
    "JourneyMaturityConfigurationRegistry",
    "default_maturity_config_registry",
    "build_sales_maturity_configuration",
    "build_real_estate_maturity_configuration",
    "build_real_estate_rental_maturity_configuration",
    "build_service_maturity_configuration",
    "build_support_maturity_configuration",
    "build_healthcare_maturity_configuration",
    # Probability
    "ObservedProbabilityCalculator",
    "calculate_wilson_score_interval",
    "default_probability_calculator",
    # Calculators
    "StageResidencyCalculator",
    "default_residency_calculator",
    "JourneyMaturityCalculator",
    "default_maturity_calculator",
    "JourneyMomentumCalculator",
    "default_momentum_calculator",
    "JourneyStabilityCalculator",
    "default_stability_calculator",
    "StageVelocityCalculator",
    "default_velocity_calculator",
    "JourneyHealthCalculator",
    "default_health_calculator",
    # Validation & Engine
    "JourneyMaturityValidator",
    "default_maturity_validator",
    "JourneyMaturityEngine",
    "default_maturity_engine",
    "JourneyMaturityReadRepository",
    "JourneyMaturityWriteRepository",
    "InMemoryJourneyMaturityRepository",
    "default_maturity_repository",
    "JourneyMaturityQueryEngine",
    "default_maturity_query_engine",
]
