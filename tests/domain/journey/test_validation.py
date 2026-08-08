from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.exceptions import (
    InvalidEvidenceError,
    InvalidTransitionError,
    JourneyError,
    TerminalStageError,
    WorkspaceIsolationError,
)
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
)
from app.domain.journey.validation import (
    validate_confidence_bounds,
    validate_entity_consistency,
    validate_evidence_integrity,
    validate_stage_transition,
    validate_terminal_stage,
    validate_workspace_isolation,
)


def test_validate_workspace_isolation_rejects_cross_workspace_evidence():
    evidence = JourneyEvidence(
        evidence_id=uuid.uuid4(),
        evidence_type=EvidenceType.INTENT,
        source_module="system",
        timestamp=datetime.now(timezone.utc),
        description="intent",
        confidence=0.9,
        metadata={"workspace_id": "ws2"},
    )
    with pytest.raises(WorkspaceIsolationError):
        validate_workspace_isolation("ws1", evidence)


def test_validate_stage_transition_rejects_invalid_transitions():
    definition = build_sales_journey_definition()
    with pytest.raises(InvalidTransitionError):
        validate_stage_transition(
            JourneyStageCode.NEW_LEAD,
            JourneyStageCode.NEGOTIATION,
            definition,
        )


def test_validate_terminal_stage_prevents_transitions_from_terminal_stages():
    with pytest.raises(TerminalStageError):
        validate_terminal_stage(JourneyStageCode.CLOSED_WON)


def test_validate_evidence_integrity_rejects_empty_evidence():
    with pytest.raises(InvalidEvidenceError):
        validate_evidence_integrity([])


def test_validate_confidence_bounds_rejects_out_of_range_values():
    with pytest.raises(InvalidEvidenceError):
        validate_confidence_bounds(-0.1)
    with pytest.raises(InvalidEvidenceError):
        validate_confidence_bounds(1.1)
    # Should not raise
    validate_confidence_bounds(0.5)


def test_validate_entity_consistency_detects_mismatches():
    state = JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )
    with pytest.raises(JourneyError):
        validate_entity_consistency(state, "CUSTOMER", "lead2")
