"""
HunterOS Engage V1 — Journey Progression Context
Phase 2.4.2: Stage Progression Engine

Input model that assembles all intelligence context needed
for a single journey progression evaluation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.domain.journey.models import (
    JourneyDefinition,
    JourneyEvidence,
    JourneyState,
)


@dataclass(frozen=True)
class JourneyProgressionContext:
    """
    Immutable input for the Stage Progression Engine.

    Memory context is optional and must only arrive through
    Memory Intelligence public APIs — never by direct repository access.
    """
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    entity_type: str = "CUSTOMER"
    entity_id: str = ""

    # Current journey state
    journey_state: Optional[JourneyState] = None

    # Journey structure definition
    journey_definition: Optional[JourneyDefinition] = None

    # Upstream intelligence context (consumed via public APIs only)
    intent_context: Optional[Dict[str, Any]] = None
    conversation_context: Optional[Dict[str, Any]] = None
    memory_context: Optional[Dict[str, Any]] = None  # Optional — via Memory API only

    # Pre-collected evidence
    evidence: List[JourneyEvidence] = field(default_factory=list)

    # Execution metadata
    current_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluated_at: Optional[datetime] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    causation_id: str = ""
