"""
HunterOS Engage V1 — Frozen Journey Intelligence Public API v1
Phase 2.4: Customer Journey Intelligence (Extended with Phase 2.4.3 Journey Maturity)

Official programmatic interface for downstream modules consuming Journey Intelligence.
Downstream bounded contexts must only consume this frozen public API.

This API exposes:
- Journey lifecycle management (create, progress)
- Journey state queries
- Definition and stage lookups
- Descriptive Journey Maturity, Momentum, Stability, Residency, Velocity, Health & Observed Probability
- View rendering (Executive, Sales, Operations, Audit)

This API does NOT:
- Generate recommendations or next-best actions
- Predict future stages using ML or speculative models
- Score leads or fabricate small-sample probabilities
- Execute workflows
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.engine import JourneyIntelligenceEngine, default_journey_engine
from app.domain.journey.maturity.engine import (
    JourneyMaturityEngine,
    default_maturity_engine,
)
from app.domain.journey.maturity.models import (
    JourneyHealth,
    JourneyMaturity,
    JourneyMaturityLevel,
    JourneyMaturityResult,
    JourneyMomentum,
    JourneyStability,
    ObservedJourneyProbability,
    StageResidency,
    StageVelocity,
)
from app.domain.journey.maturity.query import (
    JourneyMaturityQueryEngine,
    default_maturity_query_engine,
)
from app.domain.journey.models import (
    JourneyDefinition,
    JourneyEvidence,
    JourneyProgressionResult,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
    JourneyType,
)
from app.domain.journey.views.audit import AuditJourneyView
from app.domain.journey.views.executive import ExecutiveJourneyView
from app.domain.journey.views.operations import OperationsJourneyView
from app.domain.journey.views.sales import SalesJourneyView


class JourneyIntelligenceAPIv1:
    """
    Frozen Public API v1 for Customer Journey Intelligence.
    Ensures strict boundary decoupling and deterministic contract stability.

    Downstream bounded contexts (e.g., future Recommendation Intelligence)
    must consume this API, not internal Journey domain internals.
    """

    def __init__(
        self,
        engine: Optional[JourneyIntelligenceEngine] = None,
        maturity_engine: Optional[JourneyMaturityEngine] = None,
        maturity_query_engine: Optional[JourneyMaturityQueryEngine] = None,
    ) -> None:
        self._engine = engine or default_journey_engine
        journey_repo = (
            getattr(self._engine, "_read_repo", None)
            or getattr(self._engine, "_write_repo", None)
            or getattr(self._engine, "_repository", None)
            or default_journey_repository
        )
        if maturity_engine is not None:
            self._maturity_engine = maturity_engine
        elif journey_repo is not None:
            self._maturity_engine = JourneyMaturityEngine(journey_repo=journey_repo)
        else:
            self._maturity_engine = default_maturity_engine

        maturity_repo = (
            getattr(self._maturity_engine, "_maturity_repo", None)
            or default_maturity_repository
        )
        if maturity_query_engine is not None:
            self._maturity_query_engine = maturity_query_engine
        elif maturity_repo is not None:
            self._maturity_query_engine = JourneyMaturityQueryEngine(
                repository=maturity_repo,
            )
        else:
            self._maturity_query_engine = default_maturity_query_engine

        self._executive_view = ExecutiveJourneyView()
        self._sales_view = SalesJourneyView()
        self._operations_view = OperationsJourneyView()
        self._audit_view = AuditJourneyView()

    # ── Journey Lifecycle ────────────────────────────────────────────────────

    def create_journey(
        self,
        workspace_id: Union[uuid.UUID, str],
        entity_type: str,
        entity_id: str,
        journey_type: JourneyType = JourneyType.SALES,
        journey_definition_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JourneyState:
        """Create a new journey instance for an entity."""
        return self._engine.create_journey(
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            journey_type=journey_type,
            journey_definition_id=journey_definition_id,
            metadata=metadata,
        )

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
        Progress a journey based on observed intelligence context.

        Returns an evidence-backed JourneyProgressionResult describing
        whether the journey advanced, regressed, or remained unchanged.
        """
        return self._engine.progress_journey(
            journey_instance_id=journey_instance_id,
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            intent_context=intent_context,
            conversation_context=conversation_context,
            memory_context=memory_context,
            additional_evidence=additional_evidence,
        )

    # ── Query Operations ─────────────────────────────────────────────────────

    def get_journey(self, journey_instance_id: uuid.UUID) -> Optional[JourneyState]:
        """Get a journey by instance ID."""
        return self._engine.get_journey(journey_instance_id)

    def get_current_stage(
        self, journey_instance_id: uuid.UUID,
    ) -> Optional[JourneyStageCode]:
        """Get the current stage of a journey."""
        return self._engine.get_current_stage(journey_instance_id)

    def get_stage_history(
        self, journey_instance_id: uuid.UUID,
    ) -> List[JourneyStageCode]:
        """Get the chronological stage history of a journey."""
        return self._engine.get_stage_history(journey_instance_id)

    def get_transition_history(
        self, journey_instance_id: uuid.UUID,
    ) -> List[JourneyStageTransition]:
        """Get all evidence-backed transitions for a journey."""
        return self._engine.get_transition_history(journey_instance_id)

    def get_timeline(
        self, journey_instance_id: uuid.UUID,
    ) -> Optional[JourneyTimeline]:
        """Get the complete chronological timeline of a journey."""
        return self._engine.get_timeline(journey_instance_id)

    def get_journey_definition(
        self,
        journey_id: Optional[uuid.UUID] = None,
        journey_type: Optional[JourneyType] = None,
    ) -> Optional[JourneyDefinition]:
        """Get a journey definition by ID or type."""
        return self._engine.get_journey_definition(
            journey_id=journey_id, journey_type=journey_type,
        )

    def get_stage_definition(
        self, stage_code: JourneyStageCode, journey_type: JourneyType,
    ):
        """Get a stage definition by code and journey type."""
        return self._engine.get_stage_definition(stage_code, journey_type)

    def query_journeys(
        self,
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
        stage: Optional[JourneyStageCode] = None,
        status: Optional[JourneyStatus] = None,
    ) -> List[JourneyState]:
        """Query journeys with filters."""
        return self._engine.query_journeys(
            workspace_id=workspace_id, stage=stage, status=status,
        )

    def list_definitions(self) -> List[JourneyDefinition]:
        """List all registered journey definitions."""
        return self._engine.list_definitions()

    # ── Phase 2.4.3: Descriptive Maturity & Observed Probability API ─────────

    def calculate_maturity(
        self,
        journey_instance_id: Union[uuid.UUID, str],
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
        configuration_version: Optional[str] = None,
        cohort_filters: Optional[Dict[str, Any]] = None,
        evaluated_at: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> JourneyMaturityResult:
        """
        Execute deterministic 11-stage pipeline evaluating Journey Maturity,
        Momentum, Stability, Residency, Velocity, Health, and Observed Probability.
        """
        return self._maturity_engine.calculate_maturity(
            journey_id=journey_instance_id,
            workspace_id=workspace_id,
            configuration_version=configuration_version,
            cohort_filters=cohort_filters,
            evaluated_at=evaluated_at,
            use_cache=use_cache,
        )

    def get_latest_maturity(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[JourneyMaturityResult]:
        """Get the latest cached or persisted JourneyMaturityResult."""
        return self._maturity_query_engine.get_maturity_result(journey_instance_id)

    def get_maturity_score(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[float]:
        """Get the latest maturity score (0.0 - 1.0)."""
        return self._maturity_query_engine.get_maturity_score(journey_instance_id)

    def get_maturity_level(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[JourneyMaturityLevel]:
        """Get the latest maturity level."""
        return self._maturity_query_engine.get_maturity_level(journey_instance_id)

    def get_momentum(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[JourneyMomentum]:
        """Get the latest observed momentum evaluation."""
        return self._maturity_query_engine.get_momentum(journey_instance_id)

    def get_stability(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[JourneyStability]:
        """Get the latest observed stability evaluation."""
        return self._maturity_query_engine.get_stability(journey_instance_id)

    def get_stage_residency(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> List[StageResidency]:
        """Get all chronological stage residency intervals."""
        return self._maturity_query_engine.get_stage_residency(journey_instance_id)

    def get_observed_probability(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[ObservedJourneyProbability]:
        """Get the historical observed conversion probability."""
        return self._maturity_query_engine.get_observed_probability(journey_instance_id)

    def get_health(
        self, journey_instance_id: Union[uuid.UUID, str],
    ) -> Optional[JourneyHealth]:
        """Get the descriptive structural journey health."""
        return self._maturity_query_engine.get_health(journey_instance_id)

    def query_by_maturity_level(
        self,
        workspace_id: Union[uuid.UUID, str],
        level: JourneyMaturityLevel,
    ) -> List[JourneyMaturityResult]:
        """Query all journey results in a workspace with a specific maturity level."""
        return self._maturity_query_engine.get_journeys_by_maturity_level(
            workspace_id=workspace_id, level=level,
        )

    def get_stalled_journeys(
        self, workspace_id: Union[uuid.UUID, str],
    ) -> List[JourneyMaturityResult]:
        """Query all stalled journeys in a workspace."""
        return self._maturity_query_engine.get_stalled_journeys(workspace_id=workspace_id)

    def get_regressing_journeys(
        self, workspace_id: Union[uuid.UUID, str],
    ) -> List[JourneyMaturityResult]:
        """Query all regressing journeys in a workspace."""
        return self._maturity_query_engine.get_regressing_journeys(workspace_id=workspace_id)

    # ── View Rendering ───────────────────────────────────────────────────────

    def get_executive_view(
        self, journey_instance_id: uuid.UUID, include_maturity: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render the executive journey view."""
        state = self._engine.get_journey(journey_instance_id)
        if state is None:
            return None
        transitions = self._engine.get_transition_history(journey_instance_id)
        definition = self._engine.get_journey_definition(
            journey_id=state.journey_definition_id,
        )
        maturity_result = (
            self.calculate_maturity(journey_instance_id)
            if include_maturity
            else None
        )
        return self._executive_view.render(state, definition, transitions, maturity_result)

    def get_sales_view(
        self, journey_instance_id: uuid.UUID, include_maturity: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render the sales journey view."""
        state = self._engine.get_journey(journey_instance_id)
        if state is None:
            return None
        transitions = self._engine.get_transition_history(journey_instance_id)
        maturity_result = (
            self.calculate_maturity(journey_instance_id)
            if include_maturity
            else None
        )
        return self._sales_view.render(state, transitions, maturity_result)

    def get_operations_view(
        self, journey_instance_id: uuid.UUID, include_maturity: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render the operations journey view."""
        state = self._engine.get_journey(journey_instance_id)
        if state is None:
            return None
        transitions = self._engine.get_transition_history(journey_instance_id)
        timeline = self._engine.get_timeline(journey_instance_id)
        maturity_result = (
            self.calculate_maturity(journey_instance_id)
            if include_maturity
            else None
        )
        return self._operations_view.render(state, transitions, timeline, maturity_result)

    def get_audit_view(
        self, journey_instance_id: uuid.UUID, include_maturity: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render the audit journey view."""
        state = self._engine.get_journey(journey_instance_id)
        if state is None:
            return None
        transitions = self._engine.get_transition_history(journey_instance_id)
        timeline = self._engine.get_timeline(journey_instance_id)
        maturity_result = (
            self.calculate_maturity(journey_instance_id)
            if include_maturity
            else None
        )
        return self._audit_view.render(state, transitions, [], timeline, maturity_result)


    # ── Phase 2.4.4: Journey Analytics API ───────────────────────────────────

    def calculate_analytics(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
        definition_version: Optional[str] = None,
        configuration_version: Optional[str] = None,
        observation_window_days: Optional[int] = None,
        evaluated_at: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Any:  # returns JourneyAnalyticsResult
        """Execute the full analytics pipeline for a workspace."""
        from app.domain.journey.analytics.engine import default_analytics_engine
        return default_analytics_engine.calculate(
            workspace_id=workspace_id,
            journey_type=journey_type,
            definition_version=definition_version,
            configuration_version=configuration_version,
            observation_window_days=observation_window_days,
            evaluated_at=evaluated_at,
            use_cache=use_cache,
        )

    def get_latest_analytics(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:  # returns Optional[JourneyAnalyticsResult]
        """Get the latest persisted analytics result without recalculating."""
        from app.domain.journey.analytics.engine import default_analytics_engine
        return default_analytics_engine.get_latest(workspace_id, journey_type)

    def get_analytics_distribution(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Get the latest journey distribution metrics."""
        from app.domain.journey.analytics.query import default_analytics_query_engine
        return default_analytics_query_engine.get_distribution(workspace_id, journey_type)

    def get_analytics_funnel(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Get the latest funnel analytics."""
        from app.domain.journey.analytics.query import default_analytics_query_engine
        return default_analytics_query_engine.get_funnel(workspace_id, journey_type)

    def get_analytics_stage(
        self,
        workspace_id: Union[uuid.UUID, str],
        stage: Optional[str] = None,
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Get per-stage analytics."""
        from app.domain.journey.analytics.query import default_analytics_query_engine
        return default_analytics_query_engine.get_stage_analytics(workspace_id, stage, journey_type)

    def get_analytics_outcomes(
        self,
        workspace_id: Union[uuid.UUID, str],
        stage: Optional[str] = None,
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Get historical observed stage outcome analytics."""
        from app.domain.journey.analytics.query import default_analytics_query_engine
        return default_analytics_query_engine.get_outcome_metrics(workspace_id, stage, journey_type)

    def get_analytics_trends(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Get trend analytics over the observation window."""
        from app.domain.journey.analytics.query import default_analytics_query_engine
        return default_analytics_query_engine.get_trends(workspace_id, journey_type)

    def invalidate_analytics_cache(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> None:
        """Invalidate cached analytics for a workspace."""
        from app.domain.journey.analytics.engine import default_analytics_engine
        default_analytics_engine.invalidate_cache(workspace_id, journey_type)


# Module-level singleton
journey_api_v1: JourneyIntelligenceAPIv1 = JourneyIntelligenceAPIv1()
