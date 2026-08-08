"""
HunterOS Engage V1 — Journey Intelligence Engine
Phase 2.4: Orchestrator for Journey Foundation + Stage Progression

This engine coordinates all Journey Intelligence subsystems:
- Definition and stage registries
- Evidence collection
- Stage progression engine
- Validation framework
- Timeline construction
- CQRS repository operations

It is the single orchestration point consumed by the public API.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.exceptions import (
    InvalidTransitionError,
    JourneyDefinitionError,
    JourneyNotFoundError,
    WorkspaceIsolationError,
)
from app.domain.journey.models import (
    EvidenceType,
    JourneyDefinition,
    JourneyDiagnostics,
    JourneyEvidence,
    JourneyProgressionResult,
    JourneyProvenance,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
    JourneyTimelineEvent,
    JourneyType,
    TimelineEventType,
    TransitionType,
)
from app.domain.journey.progression.engine import (
    StageProgressionEngine,
    default_progression_engine,
)
from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    StageDefinitionRegistry,
    default_journey_registry,
    default_stage_registry,
)
from app.domain.journey.definitions.core import register_core_definitions
from app.domain.journey.definitions.industry.real_estate import register_real_estate_definitions
from app.domain.journey.definitions.industry.healthcare import register_healthcare_definitions
from app.domain.journey.evidence.collector import EvidenceCollector
from app.domain.journey.timeline.builder import JourneyTimelineBuilder
from app.domain.journey.repository import (
    InMemoryJourneyRepository,
    JourneyReadRepository,
    JourneyWriteRepository,
    default_journey_repository,
)
from app.domain.journey.query import JourneyQueryEngine, default_journey_query_engine


class JourneyIntelligenceEngine:
    """
    Central orchestration engine for Customer Journey Intelligence.

    Coordinates:
    - Journey creation from definitions
    - Evidence-backed stage progression
    - Timeline management
    - Repository persistence
    - Query operations

    Does NOT:
    - Generate recommendations
    - Predict future stages
    - Score leads
    - Execute workflows
    """

    def __init__(
        self,
        journey_registry: Optional[JourneyDefinitionRegistry] = None,
        stage_registry: Optional[StageDefinitionRegistry] = None,
        progression_engine: Optional[StageProgressionEngine] = None,
        read_repository: Optional[JourneyReadRepository] = None,
        write_repository: Optional[JourneyWriteRepository] = None,
        query_engine: Optional[JourneyQueryEngine] = None,
        evidence_collector: Optional[EvidenceCollector] = None,
        timeline_builder: Optional[JourneyTimelineBuilder] = None,
    ) -> None:
        self._journey_registry = journey_registry or default_journey_registry
        self._stage_registry = stage_registry or default_stage_registry
        self._progression_engine = progression_engine or default_progression_engine
        self._read_repo = read_repository or default_journey_repository
        self._write_repo = write_repository or default_journey_repository
        self._query_engine = query_engine or default_journey_query_engine
        self._evidence_collector = evidence_collector or EvidenceCollector()
        self._timeline_builder = timeline_builder or JourneyTimelineBuilder()
        self._bootstrapped = False

    def bootstrap(self) -> None:
        """Register all built-in journey and stage definitions."""
        if self._bootstrapped:
            return
        register_core_definitions(self._journey_registry, self._stage_registry)
        register_real_estate_definitions(self._journey_registry, self._stage_registry)
        register_healthcare_definitions(self._journey_registry, self._stage_registry)
        self._bootstrapped = True

    # ── Journey Creation ─────────────────────────────────────────────────────

    def create_journey(
        self,
        workspace_id: Union[uuid.UUID, str],
        entity_type: str,
        entity_id: str,
        journey_type: JourneyType = JourneyType.SALES,
        journey_definition_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JourneyState:
        """
        Create a new journey instance for an entity.

        Args:
            workspace_id: Tenant workspace ID.
            entity_type: Type of entity (e.g., 'CUSTOMER').
            entity_id: Unique entity identifier.
            journey_type: Type of journey to create.
            journey_definition_id: Specific definition ID, or auto-resolve by type.
            metadata: Optional metadata.

        Returns:
            Initialized JourneyState at the entry stage.
        """
        self.bootstrap()

        # Resolve journey definition
        if journey_definition_id:
            definition = self._journey_registry.get(journey_definition_id)
            if definition is None:
                raise JourneyDefinitionError(
                    f"Journey definition not found: {journey_definition_id}"
                )
        else:
            definition = self._journey_registry.resolve(journey_type)
            if definition is None:
                raise JourneyDefinitionError(
                    f"No journey definition found for type: {journey_type.value}"
                )

        now = datetime.now(timezone.utc)
        journey_id = uuid.uuid4()

        # Create initial timeline event
        init_event = JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=journey_id,
            workspace_id=workspace_id,
            event_type=TimelineEventType.JOURNEY_STARTED,
            stage=definition.entry_stage,
            previous_stage=None,
            timestamp=now,
            evidence=[JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.SYSTEM,
                source_module="journey.engine",
                timestamp=now,
                description="Journey initialized",
                confidence=1.0,
            )],
            confidence=1.0,
        )

        timeline = JourneyTimeline(
            timeline_id=uuid.uuid4(),
            journey_instance_id=journey_id,
            workspace_id=workspace_id,
            events=[init_event],
        )

        # Build initial state
        state = JourneyState(
            journey_instance_id=journey_id,
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            journey_definition_id=definition.journey_id,
            journey_definition_version=definition.version,
            current_stage=definition.entry_stage,
            previous_stage=None,
            stage_entered_at=now,
            journey_started_at=now,
            last_transition_at=None,
            status=JourneyStatus.ACTIVE,
            stage_history=[definition.entry_stage],
            transitions=[],
            timeline=timeline,
            metadata=metadata or {},
            provenance=JourneyProvenance(
                journey_version="2.4.2",
                definition_version=definition.version,
                generated_at=now,
                workspace_id=workspace_id,
            ),
        )

        self._write_repo.create_journey(state)
        return state

    # ── Journey Progression ──────────────────────────────────────────────────

    def progress(self, context: JourneyProgressionContext) -> JourneyProgressionResult:
        """
        Progress a journey using a JourneyProgressionContext.
        """
        self.bootstrap()

        # Workspace isolation check
        if context.workspace_id and context.journey_state and context.journey_state.workspace_id:
            if str(context.workspace_id) != str(context.journey_state.workspace_id):
                raise WorkspaceIsolationError(str(context.journey_state.workspace_id), str(context.workspace_id))

        # Ensure definition is resolved
        if context.journey_definition is None and context.journey_state:
            def_id = context.journey_state.journey_definition_id
            definition = self._journey_registry.get(def_id)
            if definition is None:
                raise JourneyDefinitionError(f"Journey definition not found: {def_id}")
            context = JourneyProgressionContext(
                workspace_id=context.workspace_id,
                entity_type=context.entity_type,
                entity_id=context.entity_id,
                journey_state=context.journey_state,
                journey_definition=definition,
                intent_context=context.intent_context,
                conversation_context=context.conversation_context,
                memory_context=context.memory_context,
                evidence=context.evidence,
                evaluated_at=context.evaluated_at,
            )

        result = self._progression_engine.progress(context)
        if result.did_progress and result.transition and context.journey_state:
            self._apply_progression(context.journey_state, result)
        return result

    def progress_journey(
        self,
        journey_instance_id: uuid.UUID,
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
        entity_type: str = "CUSTOMER",
        entity_id: str = "",
        intent_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Dict[str, Any]] = None,
        additional_evidence: Optional[List[JourneyEvidence]] = None,
    ) -> JourneyProgressionResult:
        """
        Progress a journey based on intelligence context and evidence.

        Args:
            journey_instance_id: The journey to progress.
            workspace_id: For workspace isolation validation.
            entity_type: Entity type for validation.
            entity_id: Entity ID for validation.
            intent_context: Intent Intelligence API output (dict).
            conversation_context: Conversation Intelligence API output (dict).
            memory_context: Optional Memory Intelligence API output (dict).
            additional_evidence: Pre-collected evidence items.

        Returns:
            JourneyProgressionResult indicating progression or no-change.
        """
        self.bootstrap()

        # Load state
        state = self._read_repo.get_journey(journey_instance_id)
        if state is None:
            raise JourneyNotFoundError(journey_id=str(journey_instance_id))

        # Workspace isolation
        if workspace_id and state.workspace_id:
            if str(workspace_id) != str(state.workspace_id):
                raise WorkspaceIsolationError(str(state.workspace_id), str(workspace_id))

        # Load definition
        definition = self._journey_registry.get(state.journey_definition_id)
        if definition is None:
            raise JourneyDefinitionError(
                f"Journey definition not found: {state.journey_definition_id}"
            )

        # Collect evidence from intelligence contexts
        collected_evidence = self._evidence_collector.collect_all(
            intent_context=intent_context,
            conversation_context=conversation_context,
            memory_context=memory_context,
        )
        if additional_evidence:
            collected_evidence.extend(additional_evidence)

        # Build progression context
        context = JourneyProgressionContext(
            workspace_id=workspace_id or state.workspace_id,
            entity_type=entity_type or state.entity_type,
            entity_id=entity_id or state.entity_id,
            journey_state=state,
            journey_definition=definition,
            intent_context=intent_context,
            conversation_context=conversation_context,
            memory_context=memory_context,
            evidence=collected_evidence,
            current_time=datetime.now(timezone.utc),
        )

        # Execute progression pipeline
        result = self._progression_engine.progress(context)

        # Apply progression if successful
        if result.did_progress and result.transition:
            self._apply_progression(state, result)

        return result

    def _apply_progression(
        self,
        state: JourneyState,
        result: JourneyProgressionResult,
    ) -> None:
        """Apply a successful progression to the journey state."""
        now = datetime.now(timezone.utc)

        if result.transition is None or result.new_stage is None:
            return

        # Update state (mutable)
        state.previous_stage = state.current_stage
        state.current_stage = result.new_stage
        state.stage_entered_at = now
        state.last_transition_at = now
        state.stage_history.append(result.new_stage)
        state.transitions.append(result.transition)

        # Update status based on transition type
        if result.transition_type == TransitionType.COMPLETION:
            state.status = JourneyStatus.COMPLETED
        elif result.transition_type == TransitionType.CLOSURE:
            if result.new_stage == JourneyStageCode.CLOSED_LOST:
                state.status = JourneyStatus.LOST
            elif result.new_stage == JourneyStageCode.INACTIVE:
                state.status = JourneyStatus.INACTIVE
            else:
                state.status = JourneyStatus.CANCELLED
        elif result.transition_type == TransitionType.REACTIVATION:
            state.status = JourneyStatus.ACTIVE

        # Append timeline event
        if result.timeline_event:
            current_events = list(state.timeline.events)
            current_events.append(result.timeline_event)
            state.timeline = JourneyTimeline(
                timeline_id=state.timeline.timeline_id,
                journey_instance_id=state.journey_instance_id,
                workspace_id=state.workspace_id,
                events=current_events,
            )

        # Persist
        self._write_repo.save_journey_state(state)
        self._write_repo.append_transition(
            state.journey_instance_id, result.transition,
        )
        if result.timeline_event:
            self._write_repo.append_timeline_event(
                state.journey_instance_id, result.timeline_event,
            )

    # ── Query Operations ─────────────────────────────────────────────────────

    def get_journey(self, journey_instance_id: uuid.UUID) -> Optional[JourneyState]:
        """Get a journey by instance ID."""
        return self._read_repo.get_journey(journey_instance_id)

    def get_current_stage(self, journey_instance_id: uuid.UUID) -> Optional[JourneyStageCode]:
        """Get the current stage of a journey."""
        return self._read_repo.get_current_stage(journey_instance_id)

    def get_stage_history(self, journey_instance_id: uuid.UUID) -> List[JourneyStageCode]:
        """Get the stage history of a journey."""
        return self._read_repo.get_stage_history(journey_instance_id)

    def get_transition_history(
        self, journey_instance_id: uuid.UUID,
    ) -> List[JourneyStageTransition]:
        """Get all transitions for a journey."""
        return self._read_repo.get_transitions(journey_instance_id)

    def get_timeline(self, journey_instance_id: uuid.UUID) -> Optional[JourneyTimeline]:
        """Get the complete timeline for a journey."""
        return self._read_repo.get_timeline(journey_instance_id)

    def get_journey_definition(
        self, journey_id: Optional[uuid.UUID] = None,
        journey_type: Optional[JourneyType] = None,
    ) -> Optional[JourneyDefinition]:
        """Get a journey definition by ID or type."""
        self.bootstrap()
        if journey_id:
            return self._journey_registry.get(journey_id)
        if journey_type:
            return self._journey_registry.resolve(journey_type)
        return None

    def get_stage_definition(self, stage_code: JourneyStageCode, journey_type: JourneyType):
        """Get a stage definition."""
        self.bootstrap()
        return self._stage_registry.get(stage_code, journey_type)

    def query_journeys(
        self,
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
        stage: Optional[JourneyStageCode] = None,
        status: Optional[JourneyStatus] = None,
    ) -> List[JourneyState]:
        """Query journeys by filters."""
        if stage and workspace_id:
            return self._query_engine.get_journeys_by_stage(workspace_id, stage)
        if status and workspace_id:
            return self._query_engine.get_journeys_by_status(workspace_id, status)
        if workspace_id:
            return self._query_engine.get_journeys_by_workspace(workspace_id)
        return []

    def list_definitions(self) -> List[JourneyDefinition]:
        """List all registered journey definitions."""
        self.bootstrap()
        return self._journey_registry.list()


# Module-level singleton
default_journey_engine: JourneyIntelligenceEngine = JourneyIntelligenceEngine()
default_journey_engine.bootstrap()
