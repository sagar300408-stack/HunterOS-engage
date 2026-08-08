"""
HunterOS Engage V1 — Real Estate Journey Definition
Phase 2.4.1: Industry-Specific Definitions
"""

from __future__ import annotations

import uuid
from typing import List

from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageCode,
    JourneyType,
    StageDefinition,
)
from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    StageDefinitionRegistry,
)


def build_real_estate_sales_journey() -> JourneyDefinition:
    """Build the Real Estate Property Purchase journey definition."""
    stages: List[StageDefinition] = [
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEW_LEAD,
            name="New Lead",
            description="New property inquiry",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
            allowed_previous_stages=[],
            allowed_next_stages=[
                JourneyStageCode.INTERESTED,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.INTERESTED,
            name="Interested",
            description="Interested in property",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=2,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD],
            allowed_next_stages=[
                JourneyStageCode.QUALIFIED,
                JourneyStageCode.SITE_VISIT_SCHEDULED,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.QUALIFIED,
            name="Qualified",
            description="Qualified buyer",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=3,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.INTERESTED],
            allowed_next_stages=[
                JourneyStageCode.SITE_VISIT_SCHEDULED,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.SITE_VISIT_SCHEDULED,
            name="Site Visit Scheduled",
            description="Site visit booked",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=4,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[
                JourneyStageCode.QUALIFIED,
                JourneyStageCode.INTERESTED,
            ],
            allowed_next_stages=[
                JourneyStageCode.SITE_VISIT_COMPLETED,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.SITE_VISIT_COMPLETED,
            name="Site Visit Completed",
            description="Site visit done",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=5,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.SITE_VISIT_SCHEDULED],
            allowed_next_stages=[
                JourneyStageCode.PROPERTY_SHORTLISTED,
                JourneyStageCode.NEGOTIATION,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.PROPERTY_SHORTLISTED,
            name="Property Shortlisted",
            description="Property selected for consideration",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=6,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.SITE_VISIT_COMPLETED],
            allowed_next_stages=[
                JourneyStageCode.NEGOTIATION,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEGOTIATION,
            name="Negotiation",
            description="Price negotiation",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=7,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[
                JourneyStageCode.PROPERTY_SHORTLISTED,
                JourneyStageCode.SITE_VISIT_COMPLETED,
            ],
            allowed_next_stages=[
                JourneyStageCode.BOOKING,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.BOOKING,
            name="Booking",
            description="Booking confirmed",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=8,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.NEGOTIATION],
            allowed_next_stages=[
                JourneyStageCode.CLOSED_WON,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_WON,
            name="Closed Won",
            description="Deal successfully closed",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=9,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[JourneyStageCode.BOOKING],
            allowed_next_stages=[],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_LOST,
            name="Closed Lost",
            description="Deal lost",
            journey_type=JourneyType.PROPERTY_PURCHASE,
            sequence=10,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[
                JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED,
                JourneyStageCode.QUALIFIED, JourneyStageCode.SITE_VISIT_SCHEDULED,
                JourneyStageCode.SITE_VISIT_COMPLETED, JourneyStageCode.PROPERTY_SHORTLISTED,
                JourneyStageCode.NEGOTIATION, JourneyStageCode.BOOKING,
            ],
            allowed_next_stages=[],
        ),
    ]

    return JourneyDefinition(
        journey_id=uuid.uuid4(),
        journey_type=JourneyType.PROPERTY_PURCHASE,
        name="Real Estate Sales Journey",
        description="Journey for property purchase",
        version="1.0.0",
        stage_definitions=stages,
        stage_ids=[s.stage_id for s in stages],
        entry_stage=JourneyStageCode.NEW_LEAD,
        terminal_stages=[JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST],
    )


def register_real_estate_definitions(
    journey_registry: JourneyDefinitionRegistry,
    stage_registry: StageDefinitionRegistry,
) -> None:
    """Register real estate journey definitions."""
    journey = build_real_estate_sales_journey()
    journey_registry.register(journey)
    for stage_def in journey.stage_definitions:
        stage_registry.register(stage_def)
