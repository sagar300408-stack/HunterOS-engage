"""
HunterOS Engage V1 — Healthcare Journey Definition
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


def build_healthcare_journey() -> JourneyDefinition:
    """Build the Healthcare consultation journey definition."""
    stages: List[StageDefinition] = [
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CONSULTATION_SCHEDULED,
            name="Consultation Scheduled",
            description="Doctor consultation booked",
            journey_type=JourneyType.SERVICE,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
            allowed_previous_stages=[],
            allowed_next_stages=[
                JourneyStageCode.CONSULTATION_COMPLETED,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CONSULTATION_COMPLETED,
            name="Consultation Completed",
            description="Consultation finished",
            journey_type=JourneyType.SERVICE,
            sequence=2,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.CONSULTATION_SCHEDULED],
            allowed_next_stages=[
                JourneyStageCode.TREATMENT_PLAN,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.TREATMENT_PLAN,
            name="Treatment Plan",
            description="Treatment plan provided",
            journey_type=JourneyType.SERVICE,
            sequence=3,
            is_entry_stage=False,
            is_terminal=False,
            allowed_previous_stages=[JourneyStageCode.CONSULTATION_COMPLETED],
            allowed_next_stages=[
                JourneyStageCode.CLOSED_WON,
                JourneyStageCode.CLOSED_LOST,
            ],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_WON,
            name="Treatment Completed",
            description="Treatment completed successfully",
            journey_type=JourneyType.SERVICE,
            sequence=4,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[JourneyStageCode.TREATMENT_PLAN],
            allowed_next_stages=[],
        ),
        StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.CLOSED_LOST,
            name="Cancelled",
            description="Consultation or treatment cancelled",
            journey_type=JourneyType.SERVICE,
            sequence=5,
            is_entry_stage=False,
            is_terminal=True,
            allowed_previous_stages=[
                JourneyStageCode.CONSULTATION_SCHEDULED,
                JourneyStageCode.CONSULTATION_COMPLETED,
                JourneyStageCode.TREATMENT_PLAN,
            ],
            allowed_next_stages=[],
        ),
    ]

    return JourneyDefinition(
        journey_id=uuid.uuid4(),
        journey_type=JourneyType.SERVICE,
        name="Healthcare Journey",
        description="Journey for healthcare consultation",
        version="1.0.0",
        stage_definitions=stages,
        stage_ids=[s.stage_id for s in stages],
        entry_stage=JourneyStageCode.CONSULTATION_SCHEDULED,
        terminal_stages=[JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST],
    )


def register_healthcare_definitions(
    journey_registry: JourneyDefinitionRegistry,
    stage_registry: StageDefinitionRegistry,
) -> None:
    """Register healthcare journey definitions."""
    journey = build_healthcare_journey()
    journey_registry.register(journey)
    for stage_def in journey.stage_definitions:
        stage_registry.register(stage_def)
