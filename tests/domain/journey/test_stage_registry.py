from __future__ import annotations

import threading
import uuid
import pytest

from app.domain.journey.models import (
    JourneyType,
    JourneyStageCode,
    StageDefinition,
    JourneyDefinition,
)
from app.domain.journey.definitions.registry import (
    StageDefinitionRegistry,
    JourneyDefinitionRegistry,
)
from app.domain.journey.definitions.core import (
    build_sales_journey_definition,
    register_core_definitions,
)
from app.domain.journey.exceptions import JourneyDefinitionError


def test_stage_registry_operations() -> None:
    registry = StageDefinitionRegistry()

    stage = StageDefinition(
        stage_id=uuid.uuid4(),
        stage_code=JourneyStageCode.NEW_LEAD,
        name="New Lead",
        description="A new lead",
        journey_type=JourneyType.SALES,
        sequence=1,
        is_entry_stage=True,
        is_terminal=False,
    )

    # Register
    registry.register(stage)
    assert registry.exists(JourneyStageCode.NEW_LEAD, JourneyType.SALES)

    # Get
    retrieved = registry.get(JourneyStageCode.NEW_LEAD, JourneyType.SALES)
    assert retrieved == stage

    # List
    stages = registry.list()
    assert len(stages) == 1
    assert stages[0] == stage

    # Remove
    registry.remove(JourneyStageCode.NEW_LEAD, JourneyType.SALES)
    assert not registry.exists(JourneyStageCode.NEW_LEAD, JourneyType.SALES)
    assert registry.get(JourneyStageCode.NEW_LEAD, JourneyType.SALES) is None


def test_journey_registry_operations() -> None:
    registry = JourneyDefinitionRegistry()

    journey = build_sales_journey_definition()

    # Register
    registry.register(journey)
    assert registry.exists(journey.journey_id)

    # Get
    retrieved = registry.get(journey.journey_id)
    assert retrieved == journey

    # Get by type
    by_type = registry.get_by_type(JourneyType.SALES)
    assert by_type == journey

    # Resolve
    resolved = registry.resolve(JourneyType.SALES)
    assert resolved == journey

    # List
    journeys = registry.list()
    assert len(journeys) == 1

    # Remove
    registry.remove(journey.journey_id)
    assert not registry.exists(journey.journey_id)
    assert registry.get(journey.journey_id) is None


def test_registry_thread_safety() -> None:
    registry = StageDefinitionRegistry()

    def worker(i: int) -> None:
        stage = StageDefinition(
            stage_id=uuid.uuid4(),
            stage_code=JourneyStageCode.NEW_LEAD,
            name=f"New Lead {i}",
            description="Test",
            journey_type=JourneyType.SALES,
            sequence=1,
            is_entry_stage=True,
            is_terminal=False,
        )
        registry.register(stage)

    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Only one stage code was used, so it should exist
    assert registry.exists(JourneyStageCode.NEW_LEAD, JourneyType.SALES)


def test_register_core_definitions() -> None:
    journey_reg = JourneyDefinitionRegistry()
    stage_reg = StageDefinitionRegistry()

    # Registries start empty
    assert len(journey_reg.list()) == 0
    assert len(stage_reg.list()) == 0

    # Register core
    register_core_definitions(journey_reg, stage_reg)

    # Registries should be populated
    assert len(journey_reg.list()) > 0
    assert len(stage_reg.list()) > 0

    # Sales journey should be resolvable
    sales_journey = journey_reg.resolve(JourneyType.SALES)
    assert sales_journey is not None
    assert sales_journey.journey_type == JourneyType.SALES
