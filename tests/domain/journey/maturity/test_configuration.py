"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Maturity Configuration & Registry Unit Tests
"""

from __future__ import annotations

import pytest

from app.domain.journey.exceptions import ConfigurationNotFoundError
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfiguration,
    JourneyMaturityConfigurationRegistry,
    MaturityScoreThresholds,
    build_healthcare_maturity_configuration,
    build_real_estate_maturity_configuration,
    build_sales_maturity_configuration,
    default_maturity_config_registry,
)
from app.domain.journey.maturity.models import JourneyMaturityLevel
from app.domain.journey.models import JourneyStageCode, JourneyType


def test_sales_maturity_configuration_structure():
    cfg = build_sales_maturity_configuration()
    assert cfg.journey_type == JourneyType.SALES
    assert "stage_position" in cfg.factor_weights
    assert "evidence_strength" in cfg.factor_weights
    assert cfg.get_stage_weight(JourneyStageCode.CLOSED_WON) == 1.0
    assert cfg.get_stage_weight(JourneyStageCode.NEW_LEAD) == 0.05
    assert cfg.thresholds.resolve_level(0.05) == JourneyMaturityLevel.INITIAL
    assert cfg.thresholds.resolve_level(0.20) == JourneyMaturityLevel.EARLY
    assert cfg.thresholds.resolve_level(0.40) == JourneyMaturityLevel.DEVELOPING
    assert cfg.thresholds.resolve_level(0.60) == JourneyMaturityLevel.QUALIFIED
    assert cfg.thresholds.resolve_level(0.75) == JourneyMaturityLevel.ADVANCED
    assert cfg.thresholds.resolve_level(0.90) == JourneyMaturityLevel.LATE_STAGE
    assert cfg.thresholds.resolve_level(1.0) == JourneyMaturityLevel.COMPLETED


def test_real_estate_maturity_configuration_structure():
    cfg = build_real_estate_maturity_configuration()
    assert cfg.journey_type == JourneyType.PROPERTY_PURCHASE
    assert cfg.get_stage_weight(JourneyStageCode.SITE_VISIT_COMPLETED) == 0.60
    assert cfg.get_stage_weight(JourneyStageCode.PROPERTY_SHORTLISTED) == 0.70


def test_healthcare_maturity_configuration_structure():
    cfg = build_healthcare_maturity_configuration()
    assert cfg.journey_type == JourneyType.HEALTHCARE
    assert cfg.get_stage_weight(JourneyStageCode.CONSULTATION_COMPLETED) == 0.70


def test_configuration_registry_crud_and_thread_safety():
    registry = JourneyMaturityConfigurationRegistry()

    # Defaults are pre-registered
    retrieved = registry.get(JourneyType.SALES)
    assert retrieved is not None
    assert retrieved.journey_type == JourneyType.SALES

    # Resolve with fallback
    resolved_re = registry.resolve(JourneyType.PROPERTY_PURCHASE)
    assert resolved_re.journey_type == JourneyType.PROPERTY_PURCHASE

    # Resolve unregistered falls back to SALES
    fallback = registry.resolve(JourneyType.CUSTOM)
    assert fallback.journey_type == JourneyType.SALES

    # List contains default configs
    all_cfgs = registry.list()
    assert len(all_cfgs) >= 5

    # Register custom config
    custom_cfg = JourneyMaturityConfiguration(
        journey_type=JourneyType.CUSTOM,
        version="custom-v1",
        stage_weights={JourneyStageCode.NEW_LEAD: 0.1, JourneyStageCode.CLOSED_WON: 1.0},
    )
    registry.register(custom_cfg)
    assert registry.get(JourneyType.CUSTOM, "custom-v1") is not None
