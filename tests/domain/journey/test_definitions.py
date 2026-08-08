from __future__ import annotations

import pytest

from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageCode,
    JourneyType,
)
from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.definitions.industry.real_estate import build_real_estate_sales_journey


def test_build_sales_journey_definition() -> None:
    journey_def = build_sales_journey_definition()
    assert isinstance(journey_def, JourneyDefinition)
    assert journey_def.journey_type == JourneyType.SALES
    assert journey_def.entry_stage == JourneyStageCode.NEW_LEAD
    assert len(journey_def.stage_definitions) > 0


def test_build_real_estate_sales_journey() -> None:
    journey_def = build_real_estate_sales_journey()
    assert isinstance(journey_def, JourneyDefinition)
    assert journey_def.journey_type == JourneyType.PROPERTY_PURCHASE
    assert journey_def.entry_stage == JourneyStageCode.NEW_LEAD
    
    # Check for SITE_VISIT stages specific to real estate
    stage_codes = {stage.stage_code for stage in journey_def.stage_definitions}
    assert JourneyStageCode.SITE_VISIT_SCHEDULED in stage_codes
    assert JourneyStageCode.SITE_VISIT_COMPLETED in stage_codes


def test_is_valid_transition(sales_definition: JourneyDefinition) -> None:
    # Test valid transitions based on typical sales journey
    assert sales_definition.is_valid_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED) is True
    assert sales_definition.is_valid_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_LOST) is True


def test_is_valid_transition_rejects_invalid(sales_definition: JourneyDefinition) -> None:
    # A NEW_LEAD shouldn't jump directly to CLOSED_WON in standard definition
    assert sales_definition.is_valid_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_WON) is False


def test_get_stage_sequence(sales_definition: JourneyDefinition) -> None:
    stages = sales_definition.get_stage_sequence()
    assert isinstance(stages, list)
    assert len(stages) > 0
    # First stage should be entry stage
    assert stages[0] == JourneyStageCode.NEW_LEAD


def test_terminal_stages_cannot_transition(sales_definition: JourneyDefinition) -> None:
    # Ensure terminal stages do not have valid outward transitions
    assert sales_definition.is_valid_transition(JourneyStageCode.CLOSED_WON, JourneyStageCode.QUALIFIED) is False
    assert sales_definition.is_valid_transition(JourneyStageCode.CLOSED_LOST, JourneyStageCode.NEW_LEAD) is False
    assert sales_definition.is_valid_transition(JourneyStageCode.INACTIVE, JourneyStageCode.QUALIFIED) is False
