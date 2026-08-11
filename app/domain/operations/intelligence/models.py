from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from app.domain.operations.models import ActionType


class ActionIntelligenceOutcome(str, Enum):
    ACTION_CREATED = "ACTION_CREATED"
    ACTION_ALREADY_EXISTS = "ACTION_ALREADY_EXISTS"
    UNSUPPORTED = "UNSUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID = "INVALID"


@dataclass(frozen=True)
class OperationalRequirement:
    """
    Represents an actionable operational need derived from Phase 2 Intelligence.
    This bridges the gap between 'what is known' and 'what needs to happen'.
    """
    requirement_id: UUID
    workspace_id: UUID
    source_recommendation_id: UUID
    supported_action_type: ActionType
    reason: str


@dataclass(frozen=True)
class ActionIntelligenceResult:
    """
    The structured outcome of the Action Intelligence evaluation.
    """
    outcome: ActionIntelligenceOutcome
    recommendation_id: UUID
    explanation: str
    requirement: Optional[OperationalRequirement] = None
    action_id: Optional[UUID] = None
