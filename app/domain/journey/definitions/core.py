"""
HunterOS Engage V1 — Core Cross-Industry Journey Definitions
Phase 2.4.1: Journey Foundation

Pre-built journey definitions for Sales, Service, and Support.
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


def build_sales_journey_definition() -> JourneyDefinition:
    """Build the standard cross-industry Sales journey definition."""
    stages: List[StageDefinition] = [
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEW_LEAD,
            name="New Lead",
            description="A new lead has entered the system",
            journey_type=JourneyType.SALES,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[],
            allowed_next_stages=[
                JourneyStageCode.INTERESTED,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.INTERESTED,
            name="Interested",
            description="Lead has shown interest",
            journey_type=JourneyType.SALES,
            sequence=2,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD],
            allowed_next_stages=[
                JourneyStageCode.QUALIFIED,
                JourneyStageCode.ENGAGED,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.QUALIFIED,
            name="Qualified",
            description="Lead is commercially qualified",
            journey_type=JourneyType.SALES,
            sequence=3,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.INTERESTED, JourneyStageCode.ENGAGED],
            allowed_next_stages=[
                JourneyStageCode.MEETING_SCHEDULED,
                JourneyStageCode.ENGAGED,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.ENGAGED,
            name="Engaged",
            description="Active engagement with prospect",
            journey_type=JourneyType.SALES,
            sequence=4,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED],
            allowed_next_stages=[
                JourneyStageCode.MEETING_SCHEDULED,
                JourneyStageCode.QUALIFIED,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.MEETING_SCHEDULED,
            name="Meeting Scheduled",
            description="Meeting has been scheduled",
            journey_type=JourneyType.SALES,
            sequence=5,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.QUALIFIED, JourneyStageCode.INTERESTED, JourneyStageCode.ENGAGED],
            allowed_next_stages=[
                JourneyStageCode.MEETING_COMPLETED,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.MEETING_COMPLETED,
            name="Meeting Completed",
            description="Meeting has been completed",
            journey_type=JourneyType.SALES,
            sequence=6,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.MEETING_SCHEDULED],
            allowed_next_stages=[
                JourneyStageCode.PROPOSAL,
                JourneyStageCode.NEGOTIATION,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.PROPOSAL,
            name="Proposal",
            description="Proposal has been sent",
            journey_type=JourneyType.SALES,
            sequence=7,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.MEETING_COMPLETED, JourneyStageCode.QUALIFIED],
            allowed_next_stages=[
                JourneyStageCode.NEGOTIATION,
                JourneyStageCode.BOOKING,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEGOTIATION,
            name="Negotiation",
            description="In active negotiation",
            journey_type=JourneyType.SALES,
            sequence=8,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[
                JourneyStageCode.PROPOSAL,
                JourneyStageCode.MEETING_COMPLETED,
                JourneyStageCode.QUALIFIED,
            ],
            allowed_next_stages=[
                JourneyStageCode.BOOKING,
                JourneyStageCode.CLOSED_WON,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.BOOKING,
            name="Booking",
            description="Booking in progress",
            journey_type=JourneyType.SALES,
            sequence=9,
            is_entry_stage=False,
            is_terminal=False,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.NEGOTIATION, JourneyStageCode.PROPOSAL],
            allowed_next_stages=[
                JourneyStageCode.CLOSED_WON,
                JourneyStageCode.INACTIVE,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_WON,
            name="Closed Won",
            description="Successfully closed",
            journey_type=JourneyType.SALES,
            sequence=10,
            is_entry_stage=False,
            is_terminal=True,
            is_active=True,
            allowed_previous_stages=[JourneyStageCode.BOOKING, JourneyStageCode.NEGOTIATION],
            allowed_next_stages=[],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_LOST,
            name="Closed Lost",
            description="Deal lost",
            journey_type=JourneyType.SALES,
            sequence=11,
            is_entry_stage=False,
            is_terminal=True,
            is_active=True,
            allowed_previous_stages=[
                JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED,
                JourneyStageCode.QUALIFIED, JourneyStageCode.ENGAGED,
                JourneyStageCode.MEETING_SCHEDULED, JourneyStageCode.MEETING_COMPLETED,
                JourneyStageCode.PROPOSAL, JourneyStageCode.NEGOTIATION,
                JourneyStageCode.BOOKING,
            ],
            allowed_next_stages=[],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.INACTIVE,
            name="Inactive",
            description="Inactive prospect",
            journey_type=JourneyType.SALES,
            sequence=12,
            is_entry_stage=False,
            is_terminal=True,
            is_active=True,
            allowed_previous_stages=[
                JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED,
                JourneyStageCode.QUALIFIED, JourneyStageCode.ENGAGED,
                JourneyStageCode.MEETING_SCHEDULED, JourneyStageCode.MEETING_COMPLETED,
                JourneyStageCode.PROPOSAL, JourneyStageCode.NEGOTIATION,
            ],
            allowed_next_stages=[],
        ),
    ]

    return JourneyDefinition(
        journey_id=uuid.uuid4(),
        journey_type=JourneyType.SALES,
        name="Sales Journey",
        description="Standard cross-industry sales journey",
        version="1.0.0",
        stage_definitions=stages,
        stage_ids=[s.stage_id for s in stages],
        entry_stage=JourneyStageCode.NEW_LEAD,
        terminal_stages=[JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST, JourneyStageCode.INACTIVE],
    )


def build_service_journey_definition() -> JourneyDefinition:
    """Build a simple Service journey definition."""
    stages: List[StageDefinition] = [
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEW_LEAD,
            name="New Request",
            description="New service request",
            journey_type=JourneyType.SERVICE,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
            allowed_previous_stages=[],
            allowed_next_stages=[JourneyStageCode.INTERESTED, JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.INTERESTED,
            name="In Progress",
            description="Service in progress",
            journey_type=JourneyType.SERVICE,
            sequence=2,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD],
            allowed_next_stages=[JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_WON,
            name="Service Completed",
            description="Service completed successfully",
            journey_type=JourneyType.SERVICE,
            sequence=3,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED],
            allowed_next_stages=[],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_LOST,
            name="Service Cancelled",
            description="Service request cancelled",
            journey_type=JourneyType.SERVICE,
            sequence=4,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED],
            allowed_next_stages=[],
        ),
    ]

    return JourneyDefinition(
        journey_id=uuid.uuid4(),
        journey_type=JourneyType.SERVICE,
        name="Service Journey",
        description="Standard service journey",
        version="1.0.0",
        stage_definitions=stages,
        stage_ids=[s.stage_id for s in stages],
        entry_stage=JourneyStageCode.NEW_LEAD,
        terminal_stages=[JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST],
    )


def build_support_journey_definition() -> JourneyDefinition:
    """Build a simple Support journey definition."""
    stages: List[StageDefinition] = [
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEW_LEAD,
            name="New Ticket",
            description="New support ticket",
            journey_type=JourneyType.SUPPORT,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
            allowed_previous_stages=[],
            allowed_next_stages=[JourneyStageCode.INTERESTED, JourneyStageCode.CLOSED_WON],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.INTERESTED,
            name="Under Investigation",
            description="Ticket under investigation",
            journey_type=JourneyType.SUPPORT,
            sequence=2,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD],
            allowed_next_stages=[JourneyStageCode.CLOSED_WON],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_WON,
            name="Ticket Resolved",
            description="Support ticket resolved",
            journey_type=JourneyType.SUPPORT,
            sequence=3,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED],
            allowed_next_stages=[],
        ),
    ]

    return JourneyDefinition(
        journey_id=uuid.uuid4(),
        journey_type=JourneyType.SUPPORT,
        name="Support Journey",
        description="Standard support journey",
        version="1.0.0",
        stage_definitions=stages,
        stage_ids=[s.stage_id for s in stages],
        entry_stage=JourneyStageCode.NEW_LEAD,
        terminal_stages=[JourneyStageCode.CLOSED_WON],
    )


def register_core_definitions(
    journey_registry: JourneyDefinitionRegistry,
    stage_registry: StageDefinitionRegistry,
) -> None:
    """Register all core cross-industry definitions."""
    for builder in [
        build_sales_journey_definition,
        build_service_journey_definition,
        build_support_journey_definition,
    ]:
        definition = builder()
        journey_registry.register(definition)
        for stage_def in definition.stage_definitions:
            stage_registry.register(stage_def)
