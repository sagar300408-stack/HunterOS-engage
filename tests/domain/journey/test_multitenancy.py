from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.exceptions import WorkspaceIsolationError
from app.domain.journey.models import JourneyType
from app.domain.journey.registry import register_core_definitions
from app.domain.journey.repository import InMemoryJourneyRepository


def test_workspace_isolation_progress_with_wrong_workspace_id_raises_error():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    engine = JourneyIntelligenceEngine(read_repository=repo, write_repository=repo)

    state = engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)

    context = JourneyProgressionContext(
        workspace_id="ws2",  # Wrong workspace
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={},
        conversation_context={},
        memory_context={},
        evidence=[],
        evaluated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(WorkspaceIsolationError):
        engine.progress(context)


def test_journeys_from_different_workspaces_are_isolated_in_queries():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    engine = JourneyIntelligenceEngine(read_repository=repo, write_repository=repo)

    engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)
    engine.create_journey("ws2", "CUSTOMER", "lead2", JourneyType.SALES)

    ws1_journeys = repo.query_by_workspace("ws1")
    assert len(ws1_journeys) == 1
    assert str(ws1_journeys[0].workspace_id) == "ws1"

    ws2_journeys = repo.query_by_workspace("ws2")
    assert len(ws2_journeys) == 1
    assert str(ws2_journeys[0].workspace_id) == "ws2"
