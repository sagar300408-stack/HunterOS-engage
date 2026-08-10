"""
HunterOS Engage V1 — Journey Intelligence FastAPI Router
Phase 2.4: Customer Journey Intelligence REST API (Extended with Phase 2.4.3 Journey Maturity)

Routes under /api/v1/journeys/

Endpoints:
    POST   /                              — Create journey
    GET    /{journey_id}                   — Get journey
    GET    /{journey_id}/stage             — Current stage
    GET    /{journey_id}/history           — Stage history
    GET    /{journey_id}/timeline          — Timeline
    GET    /{journey_id}/transitions       — Transition history
    POST   /{journey_id}/progress          — Progress journey
    GET    /definitions                    — List definitions
    GET    /definitions/{definition_id}    — Get definition
    GET    /query                          — Query journeys
    GET    /{journey_id}/views/{view_name} — Render view

Phase 2.4.3 Maturity & Probability Endpoints:
    GET    /{journey_id}/maturity          — Get complete maturity result
    POST   /{journey_id}/maturity/evaluate — Evaluate maturity with options
    GET    /{journey_id}/momentum          — Get momentum evaluation
    GET    /{journey_id}/stability         — Get stability evaluation
    GET    /{journey_id}/residency         — Get stage residency intervals
    GET    /{journey_id}/probability       — Get observed historical probability
    GET    /{journey_id}/health            — Get structural journey health
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.domain.journey.api import journey_api_v1
from app.domain.journey.exceptions import (
    DuplicateTransitionError,
    InvalidTransitionError,
    JourneyDefinitionError,
    JourneyNotFoundError,
    JourneyValidationError,
    WorkspaceIsolationError,
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
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStatus,
    JourneyType,
)
from app.domain.journey.schemas import (
    CreateJourneyRequest,
    EvaluateMaturityRequest,
    JourneyDefinitionDTO,
    JourneyEvidenceDTO,
    JourneyHealthDTO,
    JourneyMaturityDTO,
    JourneyMaturityResultDTO,
    JourneyMomentumDTO,
    JourneyProgressionResultDTO,
    JourneyStabilityDTO,
    JourneyStageDTO,
    JourneyStateDTO,
    JourneyTimelineDTO,
    JourneyTimelineEventDTO,
    JourneyTransitionDTO,
    ObservedJourneyProbabilityDTO,
    ProgressJourneyRequest,
    StageDefinitionDTO,
    StageResidencyDTO,
    StageVelocityDTO,
    CalculateAnalyticsRequest,
    CohortAnalyticsRequest,
)

router = APIRouter(prefix="/api/v1/journeys", tags=["Journey Intelligence"])


# ── Helper: Convert domain models to DTOs ────────────────────────────────────


def _state_to_dto(state) -> Dict[str, Any]:
    """Convert JourneyState to a serializable dict."""
    return {
        "journey_instance_id": str(state.journey_instance_id),
        "workspace_id": str(state.workspace_id) if state.workspace_id else None,
        "entity_type": state.entity_type,
        "entity_id": state.entity_id,
        "journey_definition_id": str(state.journey_definition_id),
        "journey_definition_version": state.journey_definition_version,
        "current_stage": state.current_stage.value,
        "previous_stage": state.previous_stage.value if state.previous_stage else None,
        "stage_entered_at": state.stage_entered_at.isoformat(),
        "journey_started_at": state.journey_started_at.isoformat(),
        "last_transition_at": state.last_transition_at.isoformat() if state.last_transition_at else None,
        "status": state.status.value,
        "stage_history": [s.value for s in state.stage_history],
        "metadata": state.metadata,
    }


def _transition_to_dto(t) -> Dict[str, Any]:
    """Convert JourneyStageTransition to a serializable dict."""
    return {
        "transition_id": str(t.transition_id),
        "journey_instance_id": str(t.journey_instance_id),
        "from_stage": t.from_stage.value if t.from_stage else None,
        "to_stage": t.to_stage.value,
        "transition_type": t.transition_type.value,
        "occurred_at": t.occurred_at.isoformat(),
        "evidence": [_evidence_to_dto(e) for e in t.evidence],
        "confidence": t.confidence,
        "confidence_factors": {
            "intent_match": t.confidence_factors.intent_match,
            "timeline_match": t.confidence_factors.timeline_match,
            "conversation_match": t.confidence_factors.conversation_match,
            "rule_strength": t.confidence_factors.rule_strength,
        } if t.confidence_factors else None,
        "reason": t.reason,
    }


def _evidence_to_dto(e) -> Dict[str, Any]:
    """Convert JourneyEvidence to a serializable dict."""
    return {
        "evidence_id": str(e.evidence_id),
        "evidence_type": e.evidence_type.value,
        "source_id": e.source_id,
        "source_module": e.source_module,
        "timestamp": e.timestamp.isoformat(),
        "description": e.description,
        "confidence": e.confidence,
        "metadata": e.metadata,
    }


def _timeline_event_to_dto(ev) -> Dict[str, Any]:
    """Convert JourneyTimelineEvent to a serializable dict."""
    return {
        "event_id": str(ev.event_id),
        "event_type": ev.event_type.value,
        "stage": ev.stage.value if ev.stage else None,
        "previous_stage": ev.previous_stage.value if ev.previous_stage else None,
        "timestamp": ev.timestamp.isoformat(),
        "confidence": ev.confidence,
    }


def _definition_to_dto(d) -> Dict[str, Any]:
    """Convert JourneyDefinition to a serializable dict."""
    return {
        "journey_id": str(d.journey_id),
        "journey_type": d.journey_type.value,
        "name": d.name,
        "description": d.description,
        "version": d.version,
        "entry_stage": d.entry_stage.value,
        "terminal_stages": [s.value for s in d.terminal_stages],
        "stages": [
            {
                "stage_id": str(sd.stage_id),
                "stage_code": sd.stage_code.value,
                "name": sd.name,
                "description": sd.description,
                "sequence": sd.sequence,
                "allowed_previous_stages": [s.value for s in sd.allowed_previous_stages],
                "allowed_next_stages": [s.value for s in sd.allowed_next_stages],
                "is_terminal": sd.is_terminal,
                "is_entry_stage": sd.is_entry_stage,
            }
            for sd in d.stage_definitions
        ],
    }


def _progression_result_to_dto(r) -> Dict[str, Any]:
    """Convert JourneyProgressionResult to a serializable dict."""
    return {
        "progression_id": str(r.progression_id),
        "journey_instance_id": str(r.journey_instance_id),
        "did_progress": r.did_progress,
        "previous_stage": r.previous_stage.value if r.previous_stage else None,
        "current_stage": r.current_stage.value,
        "new_stage": r.new_stage.value if r.new_stage else None,
        "transition": _transition_to_dto(r.transition) if r.transition else None,
        "transition_type": r.transition_type.value if r.transition_type else None,
        "confidence": r.confidence,
        "confidence_factors": {
            "intent_match": r.confidence_factors.intent_match,
            "timeline_match": r.confidence_factors.timeline_match,
            "conversation_match": r.confidence_factors.conversation_match,
            "rule_strength": r.confidence_factors.rule_strength,
        } if r.confidence_factors else None,
        "evidence": [_evidence_to_dto(e) for e in r.evidence],
        "diagnostics": {
            "pipeline_version": r.diagnostics.pipeline_version,
            "rules_evaluated": r.diagnostics.rules_evaluated,
            "rules_matched": r.diagnostics.rules_matched,
            "candidate_transition_count": r.diagnostics.candidate_transition_count,
            "accepted_transition_count": r.diagnostics.accepted_transition_count,
            "rejected_transition_count": r.diagnostics.rejected_transition_count,
            "evidence_count": r.diagnostics.evidence_count,
            "execution_time_ms": r.diagnostics.execution_time_ms,
            "validation_errors": r.diagnostics.validation_errors,
        },
        "generated_at": r.generated_at.isoformat(),
    }


def _maturity_to_dto(m: JourneyMaturity) -> Dict[str, Any]:
    return {
        "maturity_score": m.maturity_score,
        "maturity_level": m.maturity_level.value,
        "current_stage": m.current_stage.value,
        "stage_position": m.stage_position,
        "total_active_stages": m.total_active_stages,
        "completed_stage_count": m.completed_stage_count,
        "journey_progress_ratio": m.journey_progress_ratio,
        "stage_duration_days": m.stage_duration_days,
        "journey_age_days": m.journey_age_days,
        "evidence_strength": m.evidence_strength,
        "calculated_at": m.calculated_at.isoformat(),
        "factors": {
            "stage_position_factor": m.factors.stage_position_factor,
            "stage_completion_factor": m.factors.stage_completion_factor,
            "transition_history_factor": m.factors.transition_history_factor,
            "evidence_strength_factor": m.factors.evidence_strength_factor,
            "journey_age_factor": m.factors.journey_age_factor,
            "stage_stability_factor": m.factors.stage_stability_factor,
            "progression_consistency_factor": m.factors.progression_consistency_factor,
            "custom_factors": m.factors.custom_factors,
        },
        "provenance": {
            "calculation_id": str(m.provenance.calculation_id),
            "journey_id": str(m.provenance.journey_id),
            "workspace_id": str(m.provenance.workspace_id),
            "entity_id": m.provenance.entity_id,
            "engine_version": m.provenance.engine_version,
            "pipeline_version": m.provenance.pipeline_version,
            "configuration_version": m.provenance.configuration_version,
            "generated_at": m.provenance.generated_at.isoformat(),
            "source_modules": m.provenance.source_modules,
            "source_artifacts": m.provenance.source_artifacts,
            "calculation_method": m.provenance.calculation_method,
            "correlation_id": m.provenance.correlation_id,
        },
    }


def _momentum_to_dto(mom: JourneyMomentum) -> Dict[str, Any]:
    return {
        "state": mom.state.value,
        "momentum_score": mom.momentum_score,
        "recent_advancements_count": mom.recent_advancements_count,
        "recent_regressions_count": mom.recent_regressions_count,
        "days_since_last_transition": mom.days_since_last_transition,
        "transition_frequency_per_week": mom.transition_frequency_per_week,
        "description": mom.description,
        "calculated_at": mom.calculated_at.isoformat(),
    }


def _stability_to_dto(s: JourneyStability) -> Dict[str, Any]:
    return {
        "stability_score": s.stability_score,
        "stability_level": s.stability_level.value,
        "current_stage_duration_days": s.current_stage_duration_days,
        "stage_reentry_count": s.stage_reentry_count,
        "stage_transition_count": s.stage_transition_count,
        "supporting_evidence_count": s.supporting_evidence_count,
        "conflicting_evidence_count": s.conflicting_evidence_count,
        "calculated_at": s.calculated_at.isoformat(),
        "factors": s.factors,
    }


def _residency_to_dto(r: StageResidency) -> Dict[str, Any]:
    return {
        "residency_id": str(r.residency_id),
        "stage": r.stage.value,
        "entered_at": r.entered_at.isoformat(),
        "exited_at": r.exited_at.isoformat() if r.exited_at else None,
        "duration_days": r.duration_days,
        "transition_count": r.transition_count,
        "reentry_count": r.reentry_count,
        "evidence_count": r.evidence_count,
        "confidence": r.confidence,
        "status": r.status.value,
    }


def _velocity_to_dto(v: StageVelocity) -> Dict[str, Any]:
    return {
        "transitions_per_day": v.transitions_per_day,
        "transitions_per_week": v.transitions_per_week,
        "average_stage_duration_days": v.average_stage_duration_days,
        "current_stage_duration_days": v.current_stage_duration_days,
        "historical_average_duration_days": v.historical_average_duration_days,
        "velocity_state": v.velocity_state.value,
        "calculated_at": v.calculated_at.isoformat(),
    }


def _probability_to_dto(p: Optional[ObservedJourneyProbability]) -> Optional[Dict[str, Any]]:
    if p is None:
        return None
    return {
        "probability_id": str(p.probability_id),
        "value": p.value,
        "status": p.status.value,
        "probability_type": p.probability_type.value,
        "target_stage": p.target_stage.value if p.target_stage else None,
        "target_outcome": p.target_outcome,
        "sample_size": p.sample_size,
        "success_count": p.success_count,
        "failure_count": p.failure_count,
        "minimum_required_sample": p.minimum_required_sample,
        "minimum_sample_met": p.minimum_sample_met,
        "observation_window_days": p.observation_window_days,
        "calculation_method": p.calculation_method,
        "confidence": p.confidence,
        "confidence_interval_lower": p.confidence_interval_lower,
        "confidence_interval_upper": p.confidence_interval_upper,
        "confidence_level": p.confidence_level,
        "cohort_filters": p.cohort_filters,
        "limitations": p.limitations,
        "calculated_at": p.calculated_at.isoformat(),
    }


def _health_to_dto(h: JourneyHealth) -> Dict[str, Any]:
    return {
        "state": h.state.value,
        "summary": h.summary,
        "factors": h.factors,
        "calculated_at": h.calculated_at.isoformat(),
    }


def _maturity_result_to_dto(res: JourneyMaturityResult) -> Dict[str, Any]:
    return {
        "journey_id": str(res.journey_id),
        "workspace_id": str(res.workspace_id),
        "entity_id": res.entity_id,
        "current_stage": res.current_stage.value,
        "journey_status": res.journey_status.value,
        "maturity": _maturity_to_dto(res.maturity),
        "momentum": _momentum_to_dto(res.momentum),
        "stability": _stability_to_dto(res.stability),
        "velocity": _velocity_to_dto(res.velocity),
        "stage_residency": [_residency_to_dto(r) for r in res.stage_residency],
        "current_residency": _residency_to_dto(res.current_residency),
        "observed_probability": _probability_to_dto(res.observed_probability),
        "health": _health_to_dto(res.health),
        "diagnostics": {
            "stage_timings": res.diagnostics.stage_timings,
            "total_execution_time_ms": res.diagnostics.total_execution_time_ms,
            "evidence_count": res.diagnostics.evidence_count,
            "transition_count": res.diagnostics.transition_count,
            "residency_count": res.diagnostics.residency_count,
            "rules_evaluated": res.diagnostics.rules_evaluated,
            "rules_matched": res.diagnostics.rules_matched,
            "warnings": res.diagnostics.warnings,
            "validation_errors": res.diagnostics.validation_errors,
            "probability_available": res.diagnostics.probability_available,
            "probability_sample_size": res.diagnostics.probability_sample_size,
            "calculation_version": res.diagnostics.calculation_version,
        },
        "provenance": {
            "calculation_id": str(res.provenance.calculation_id),
            "journey_id": str(res.provenance.journey_id),
            "workspace_id": str(res.provenance.workspace_id),
            "entity_id": res.provenance.entity_id,
            "engine_version": res.provenance.engine_version,
            "pipeline_version": res.provenance.pipeline_version,
            "configuration_version": res.provenance.configuration_version,
            "generated_at": res.provenance.generated_at.isoformat(),
            "source_modules": res.provenance.source_modules,
            "source_artifacts": res.provenance.source_artifacts,
            "calculation_method": res.provenance.calculation_method,
            "correlation_id": res.provenance.correlation_id,
        },
        "calculated_at": res.calculated_at.isoformat(),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "",
    summary="Create Journey",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict[str, Any],
)
def create_journey(request: CreateJourneyRequest) -> Dict[str, Any]:
    """Create a new journey instance for an entity."""
    try:
        jtype = JourneyType(request.journey_type)
    except ValueError:
        jtype = JourneyType.SALES

    try:
        def_id = uuid.UUID(request.journey_definition_id) if request.journey_definition_id else None
    except (ValueError, AttributeError):
        def_id = None

    try:
        state = journey_api_v1.create_journey(
            workspace_id=request.workspace_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            journey_type=jtype,
            journey_definition_id=def_id,
            metadata=request.metadata,
        )
        return _state_to_dto(state)
    except JourneyDefinitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{journey_id}",
    summary="Get Journey",
    response_model=Dict[str, Any],
)
def get_journey(journey_id: str) -> Dict[str, Any]:
    """Get a journey by instance ID."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    state = journey_api_v1.get_journey(jid)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    return _state_to_dto(state)


@router.get(
    "/{journey_id}/stage",
    summary="Get Current Stage",
    response_model=Dict[str, Any],
)
def get_journey_stage(journey_id: str) -> Dict[str, Any]:
    """Get the current stage of a journey."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    state = journey_api_v1.get_journey(jid)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    return {
        "journey_instance_id": str(state.journey_instance_id),
        "current_stage": state.current_stage.value,
        "previous_stage": state.previous_stage.value if state.previous_stage else None,
        "stage_entered_at": state.stage_entered_at.isoformat(),
        "status": state.status.value,
    }


@router.get(
    "/{journey_id}/history",
    summary="Get Stage History",
    response_model=Dict[str, Any],
)
def get_journey_history(journey_id: str) -> Dict[str, Any]:
    """Get the complete stage history of a journey."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    history = journey_api_v1.get_stage_history(jid)
    if not history:
        state = journey_api_v1.get_journey(jid)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    return {
        "journey_instance_id": journey_id,
        "stage_history": [s.value for s in history],
        "total_stages": len(history),
    }


@router.get(
    "/{journey_id}/timeline",
    summary="Get Journey Timeline",
    response_model=Dict[str, Any],
)
def get_journey_timeline(journey_id: str) -> Dict[str, Any]:
    """Get the chronological timeline of a journey."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    timeline = journey_api_v1.get_timeline(jid)
    if timeline is None:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    return {
        "journey_instance_id": journey_id,
        "timeline_id": str(timeline.timeline_id),
        "events": [_timeline_event_to_dto(e) for e in timeline.events],
        "total_events": len(timeline.events),
    }


@router.get(
    "/{journey_id}/transitions",
    summary="Get Transition History",
    response_model=Dict[str, Any],
)
def get_journey_transitions(journey_id: str) -> Dict[str, Any]:
    """Get all evidence-backed transitions of a journey."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    transitions = journey_api_v1.get_transition_history(jid)
    return {
        "journey_instance_id": journey_id,
        "transitions": [_transition_to_dto(t) for t in transitions],
        "total_transitions": len(transitions),
    }


@router.post(
    "/{journey_id}/progress",
    summary="Progress Journey",
    response_model=Dict[str, Any],
)
def progress_journey(journey_id: str, request: ProgressJourneyRequest) -> Dict[str, Any]:
    """
    Progress a journey based on observed intelligence context.
    """
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        result = journey_api_v1.progress_journey(
            journey_instance_id=jid,
            workspace_id=request.workspace_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            intent_context=request.intent_context,
            conversation_context=request.conversation_context,
            memory_context=request.memory_context,
        )
        return _progression_result_to_dto(result)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkspaceIsolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DuplicateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except JourneyDefinitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/definitions",
    summary="List Journey Definitions",
    response_model=List[Dict[str, Any]],
)
def list_definitions() -> List[Dict[str, Any]]:
    """List all registered journey definitions."""
    definitions = journey_api_v1.list_definitions()
    return [_definition_to_dto(d) for d in definitions]


@router.get(
    "/definitions/{definition_id}",
    summary="Get Journey Definition",
    response_model=Dict[str, Any],
)
def get_definition(definition_id: str) -> Dict[str, Any]:
    """Get a journey definition by ID."""
    try:
        did = uuid.UUID(definition_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid definition ID format")

    definition = journey_api_v1.get_journey_definition(journey_id=did)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Definition not found: {definition_id}")
    return _definition_to_dto(definition)


@router.get(
    "/query",
    summary="Query Journeys",
    response_model=Dict[str, Any],
)
def query_journeys(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
    stage: Optional[str] = Query(None, description="Filter by current stage"),
    journey_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
) -> Dict[str, Any]:
    """Query journeys with optional filters."""
    stage_code = None
    if stage:
        try:
            stage_code = JourneyStageCode(stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    status_code = None
    if journey_status:
        try:
            status_code = JourneyStatus(journey_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {journey_status}")

    journeys = journey_api_v1.query_journeys(
        workspace_id=workspace_id,
        stage=stage_code,
        status=status_code,
    )
    return {
        "journeys": [_state_to_dto(j) for j in journeys],
        "total": len(journeys),
    }


@router.get(
    "/{journey_id}/views/{view_name}",
    summary="Render Journey View",
    response_model=Dict[str, Any],
)
def render_view(
    journey_id: str,
    view_name: str,
    include_maturity: bool = Query(True, description="Include maturity metrics in view"),
) -> Dict[str, Any]:
    """
    Render a role-specific journey view.
    Supported views: executive, sales, operations, audit
    """
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    view_name_lower = view_name.lower()
    if view_name_lower == "executive":
        result = journey_api_v1.get_executive_view(jid, include_maturity=include_maturity)
    elif view_name_lower == "sales":
        result = journey_api_v1.get_sales_view(jid, include_maturity=include_maturity)
    elif view_name_lower == "operations":
        result = journey_api_v1.get_operations_view(jid, include_maturity=include_maturity)
    elif view_name_lower == "audit":
        result = journey_api_v1.get_audit_view(jid, include_maturity=include_maturity)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown view: {view_name}. Supported: executive, sales, operations, audit",
        )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    return result


# ── Phase 2.4.3: Maturity & Probability Endpoints ────────────────────────────


@router.get(
    "/{journey_id}/maturity",
    summary="Get Journey Maturity Result",
    response_model=Dict[str, Any],
)
def get_journey_maturity(
    journey_id: str,
    workspace_id: Optional[str] = Query(None, description="Workspace ID for boundary enforcement"),
) -> Dict[str, Any]:
    """
    Get or compute the complete descriptive Journey Maturity result.
    """
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(
            journey_instance_id=jid,
            workspace_id=workspace_id,
            use_cache=True,
        )
        return _maturity_result_to_dto(res)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkspaceIsolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except JourneyValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{journey_id}/maturity/evaluate",
    summary="Evaluate Journey Maturity",
    response_model=Dict[str, Any],
)
def evaluate_journey_maturity(
    journey_id: str,
    request: EvaluateMaturityRequest,
) -> Dict[str, Any]:
    """
    Force re-evaluation of the 11-stage Journey Maturity pipeline with custom options.
    """
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(
            journey_instance_id=jid,
            workspace_id=request.workspace_id,
            configuration_version=request.configuration_version,
            cohort_filters=request.cohort_filters,
            use_cache=False,
        )
        return _maturity_result_to_dto(res)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkspaceIsolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except JourneyValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{journey_id}/momentum",
    summary="Get Journey Momentum",
    response_model=Dict[str, Any],
)
def get_journey_momentum(journey_id: str) -> Dict[str, Any]:
    """Get the observed momentum evaluation."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(journey_instance_id=jid)
        return _momentum_to_dto(res.momentum)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{journey_id}/stability",
    summary="Get Journey Stability",
    response_model=Dict[str, Any],
)
def get_journey_stability(journey_id: str) -> Dict[str, Any]:
    """Get the observed stability evaluation."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(journey_instance_id=jid)
        return _stability_to_dto(res.stability)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{journey_id}/residency",
    summary="Get Stage Residency",
    response_model=Dict[str, Any],
)
def get_journey_stage_residency(journey_id: str) -> Dict[str, Any]:
    """Get chronological stage residency intervals."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(journey_instance_id=jid)
        return {
            "journey_id": journey_id,
            "residencies": [_residency_to_dto(r) for r in res.stage_residency],
            "current_residency": _residency_to_dto(res.current_residency),
        }
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{journey_id}/probability",
    summary="Get Observed Probability",
    response_model=Dict[str, Any],
)
def get_journey_observed_probability(journey_id: str) -> Dict[str, Any]:
    """Get the evidence-derived historical observed conversion probability."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(journey_instance_id=jid)
        return _probability_to_dto(res.observed_probability) or {}
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{journey_id}/health",
    summary="Get Journey Health",
    response_model=Dict[str, Any],
)
def get_journey_health(journey_id: str) -> Dict[str, Any]:
    """Get descriptive structural journey health."""
    try:
        jid = uuid.UUID(journey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid journey ID format")

    try:
        res = journey_api_v1.calculate_maturity(journey_instance_id=jid)
        return _health_to_dto(res.health)
    except JourneyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Phase 2.4.4: Journey Analytics Endpoints ─────────────────────────────────


def _analytics_result_to_dto(result) -> Dict[str, Any]:
    """Convert JourneyAnalyticsResult to a serializable dict."""
    window = result.observation_window
    prov = result.provenance
    diag = result.diagnostics

    return {
        "analytics_id": str(result.analytics_id),
        "workspace_id": str(result.workspace_id),
        "journey_type": result.journey_type,
        "definition_version": result.definition_version,
        "observation_window": {
            "start_at": window.start_at.isoformat(),
            "end_at": window.end_at.isoformat(),
            "timezone": window.timezone,
            "duration_days": window.duration_days,
        },
        "generated_at": result.generated_at.isoformat(),
        "journey_count": result.journey_count,
        "distribution": {
            "total_journeys": result.distribution.total_journeys,
            "active_journeys": result.distribution.active_journeys,
            "completed_journeys": result.distribution.completed_journeys,
            "cancelled_journeys": result.distribution.cancelled_journeys,
            "inactive_journeys": result.distribution.inactive_journeys,
            "archived_journeys": result.distribution.archived_journeys,
            "by_status": result.distribution.by_status,
            "by_current_stage": result.distribution.by_current_stage,
            "by_journey_type": result.distribution.by_journey_type,
            "by_maturity_level": result.distribution.by_maturity_level,
            "by_momentum_state": result.distribution.by_momentum_state,
            "by_stability_level": result.distribution.by_stability_level,
            "by_velocity_state": result.distribution.by_velocity_state,
            "by_health_state": result.distribution.by_health_state,
        },
        "stage_analytics": {
            k: {
                "stage": v.stage,
                "journey_count": v.journey_count,
                "percentage_of_journeys": v.percentage_of_journeys,
                "unique_entries": v.unique_entries,
                "unique_exits": v.unique_exits,
                "current_residency_count": v.current_residency_count,
                "completed_residency_count": v.completed_residency_count,
                "average_residency_days": v.average_residency_days,
                "median_residency_days": v.median_residency_days,
                "p25_residency_days": v.p25_residency_days,
                "p75_residency_days": v.p75_residency_days,
            }
            for k, v in result.stage_analytics.items()
        },
        "transition_metrics": {
            "total_transitions": result.transition_metrics.total_transitions,
            "forward_transition_count": result.transition_metrics.forward_transition_count,
            "regression_transition_count": result.transition_metrics.regression_transition_count,
            "same_stage_reentry_count": result.transition_metrics.same_stage_reentry_count,
            "terminal_transition_count": result.transition_metrics.terminal_transition_count,
            "by_transition": [
                {
                    "from_stage": t.from_stage,
                    "to_stage": t.to_stage,
                    "transition_count": t.transition_count,
                    "unique_journeys": t.unique_journeys,
                    "transition_percentage": t.transition_percentage,
                    "is_forward": t.is_forward,
                    "is_regression": t.is_regression,
                    "is_reentry": t.is_reentry,
                    "is_terminal": t.is_terminal,
                }
                for t in result.transition_metrics.by_transition
            ],
        },
        "funnel": {
            "funnel_stages": result.funnel.funnel_stages,
            "total_entered": result.funnel.total_entered,
            "total_completed": result.funnel.total_completed,
            "overall_completion_rate": result.funnel.overall_completion_rate,
            "has_regressions": result.funnel.has_regressions,
            "has_skip_patterns": result.funnel.has_skip_patterns,
            "stage_metrics": [
                {
                    "stage": sm.stage,
                    "sequence": sm.sequence,
                    "entered_count": sm.entered_count,
                    "advanced_count": sm.advanced_count,
                    "regressed_count": sm.regressed_count,
                    "exited_count": sm.exited_count,
                    "remaining_count": sm.remaining_count,
                    "historical_completion_rate": sm.historical_completion_rate,
                }
                for sm in result.funnel.stage_metrics
            ],
        } if result.funnel else None,
        "duration_metrics": {
            "total_sample_size": result.duration_metrics.total_sample_size,
            "average_duration_days": result.duration_metrics.average_duration_days,
            "median_duration_days": result.duration_metrics.median_duration_days,
            "minimum_duration_days": result.duration_metrics.minimum_duration_days,
            "maximum_duration_days": result.duration_metrics.maximum_duration_days,
            "p25_duration_days": result.duration_metrics.p25_duration_days,
            "p75_duration_days": result.duration_metrics.p75_duration_days,
            "active_average_days": result.duration_metrics.active_average_days,
            "completed_average_days": result.duration_metrics.completed_average_days,
            "cancelled_average_days": result.duration_metrics.cancelled_average_days,
        },
        "maturity_analytics": {
            "sample_size": result.maturity_analytics.sample_size,
            "average_maturity_score": result.maturity_analytics.average_maturity_score,
            "median_maturity_score": result.maturity_analytics.median_maturity_score,
            "maturity_level_counts": result.maturity_analytics.maturity_level_counts,
            "maturity_level_percentages": result.maturity_analytics.maturity_level_percentages,
            "lowest_maturity_bucket": result.maturity_analytics.lowest_maturity_bucket,
            "highest_maturity_bucket": result.maturity_analytics.highest_maturity_bucket,
        },
        "momentum_analytics": {
            "sample_size": result.momentum_analytics.sample_size,
            "state_counts": result.momentum_analytics.state_counts,
            "state_percentages": result.momentum_analytics.state_percentages,
            "advancing_percentage": result.momentum_analytics.advancing_percentage,
            "stable_percentage": result.momentum_analytics.stable_percentage,
            "weakening_percentage": result.momentum_analytics.weakening_percentage,
            "regressing_percentage": result.momentum_analytics.regressing_percentage,
            "inactive_percentage": result.momentum_analytics.inactive_percentage,
        },
        "stability_analytics": {
            "sample_size": result.stability_analytics.sample_size,
            "level_counts": result.stability_analytics.level_counts,
            "level_percentages": result.stability_analytics.level_percentages,
            "average_stability_score": result.stability_analytics.average_stability_score,
            "reentry_frequency": result.stability_analytics.reentry_frequency,
            "oscillation_frequency": result.stability_analytics.oscillation_frequency,
        },
        "velocity_analytics": {
            "sample_size": result.velocity_analytics.sample_size,
            "state_counts": result.velocity_analytics.state_counts,
            "state_percentages": result.velocity_analytics.state_percentages,
            "average_transitions_per_day": result.velocity_analytics.average_transitions_per_day,
            "average_transitions_per_week": result.velocity_analytics.average_transitions_per_week,
            "average_stage_duration_days": result.velocity_analytics.average_stage_duration_days,
        },
        "health_analytics": {
            "sample_size": result.health_analytics.sample_size,
            "health_distribution": result.health_analytics.health_distribution,
            "health_percentages": result.health_analytics.health_percentages,
            "healthy_percentage": result.health_analytics.healthy_percentage,
            "stalled_percentage": result.health_analytics.stalled_percentage,
            "regressing_percentage": result.health_analytics.regressing_percentage,
            "inactive_percentage": result.health_analytics.inactive_percentage,
        },
        "progression_patterns": {
            "sample_size": result.progression_patterns.sample_size,
            "average_forward_transitions": result.progression_patterns.average_forward_transitions,
            "average_regressions": result.progression_patterns.average_regressions,
            "progression_consistency_score": result.progression_patterns.progression_consistency_score,
            "pattern_distribution": result.progression_patterns.pattern_distribution,
            "pattern_percentages": result.progression_patterns.pattern_percentages,
        },
        "outcome_analytics": {
            k: {
                "stage": v.stage,
                "outcome": v.outcome,
                "sample_size": v.sample_size,
                "observed_rate": v.observed_rate,
                "minimum_sample_met": v.minimum_sample_met,
                "confidence_interval_lower": v.confidence_interval_lower,
                "confidence_interval_upper": v.confidence_interval_upper,
                "confidence_level": v.confidence_level,
                "limitations": v.limitations,
                "data_status": v.data_status.value,
            }
            for k, v in result.outcome_analytics.items()
        },
        "trend_analytics": {
            "granularity": result.trend_analytics.granularity.value,
            "metrics": result.trend_analytics.metrics,
            "total_periods": result.trend_analytics.total_periods,
            "data_points": [
                {
                    "period_label": dp.period_label,
                    "metric": dp.metric,
                    "value": dp.value,
                    "sample_size": dp.sample_size,
                }
                for dp in result.trend_analytics.data_points
            ],
        } if result.trend_analytics else None,
        "diagnostics": {
            "total_execution_time_ms": diag.total_execution_time_ms,
            "journeys_processed": diag.journeys_processed,
            "transitions_processed": diag.transitions_processed,
            "maturity_results_processed": diag.maturity_results_processed,
            "metrics_calculated": diag.metrics_calculated,
            "warnings": diag.warnings,
            "validation_errors": diag.validation_errors,
            "empty_dataset": diag.empty_dataset,
            "partial_dataset": diag.partial_dataset,
        },
        "provenance": {
            "analytics_id": str(prov.analytics_id),
            "workspace_id": str(prov.workspace_id),
            "generated_at": prov.generated_at.isoformat(),
            "engine_version": prov.engine_version,
            "pipeline_version": prov.pipeline_version,
            "configuration_version": prov.configuration_version,
            "source_journey_count": prov.source_journey_count,
            "source_transition_count": prov.source_transition_count,
            "source_maturity_count": prov.source_maturity_count,
            "calculation_methods": prov.calculation_methods,
            "statistical_methods": prov.statistical_methods,
        },
    }


@router.post(
    "/analytics",
    response_model=None,
    summary="Calculate Journey Analytics",
    description="Execute the full analytics pipeline for a workspace. Returns descriptive, historical, read-only analytics across all journeys.",
)
def calculate_analytics(
    request: CalculateAnalyticsRequest,
) -> Dict[str, Any]:
    """POST /api/v1/journeys/analytics — Execute the full analytics pipeline."""
    try:
        result = journey_api_v1.calculate_analytics(
            workspace_id=request.workspace_id,
            journey_type=request.journey_type,
            definition_version=request.definition_version,
            configuration_version=request.configuration_version,
            observation_window_days=request.observation_window_days,
            use_cache=request.use_cache,
        )
        return _analytics_result_to_dto(result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics calculation failed: {str(e)}",
        )


@router.get(
    "/analytics",
    response_model=None,
    summary="Get Latest Analytics",
    description="Retrieve the latest cached analytics result for a workspace without recalculating.",
)
def get_analytics(
    workspace_id: str = Query(..., description="Workspace ID"),
    journey_type: Optional[str] = Query(None, description="Filter by journey type"),
) -> Dict[str, Any]:
    """GET /api/v1/journeys/analytics — Get latest analytics result."""
    result = journey_api_v1.get_latest_analytics(workspace_id, journey_type)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analytics found for workspace {workspace_id}. Run POST /analytics first.",
        )
    return _analytics_result_to_dto(result)


@router.get(
    "/analytics/distribution",
    response_model=None,
    summary="Get Journey Distribution",
    description="Get the latest journey distribution metrics for a workspace.",
)
def get_analytics_distribution(
    workspace_id: str = Query(..., description="Workspace ID"),
    journey_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """GET /api/v1/journeys/analytics/distribution"""
    dist = journey_api_v1.get_analytics_distribution(workspace_id, journey_type)
    if dist is None:
        raise HTTPException(status_code=404, detail="No analytics distribution found. Run POST /analytics first.")
    return {
        "total_journeys": dist.total_journeys,
        "active_journeys": dist.active_journeys,
        "completed_journeys": dist.completed_journeys,
        "cancelled_journeys": dist.cancelled_journeys,
        "by_status": dist.by_status,
        "by_current_stage": dist.by_current_stage,
        "by_maturity_level": dist.by_maturity_level,
        "by_momentum_state": dist.by_momentum_state,
        "by_health_state": dist.by_health_state,
    }


@router.get(
    "/analytics/funnel",
    response_model=None,
    summary="Get Journey Funnel",
    description="Get the observed stage funnel analytics for a workspace.",
)
def get_analytics_funnel(
    workspace_id: str = Query(..., description="Workspace ID"),
    journey_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """GET /api/v1/journeys/analytics/funnel"""
    funnel = journey_api_v1.get_analytics_funnel(workspace_id, journey_type)
    if funnel is None:
        raise HTTPException(status_code=404, detail="No funnel analytics found. Run POST /analytics first.")
    return {
        "funnel_stages": funnel.funnel_stages,
        "total_entered": funnel.total_entered,
        "total_completed": funnel.total_completed,
        "overall_completion_rate": funnel.overall_completion_rate,
        "has_regressions": funnel.has_regressions,
        "has_skip_patterns": funnel.has_skip_patterns,
        "stage_metrics": [
            {
                "stage": sm.stage,
                "sequence": sm.sequence,
                "entered_count": sm.entered_count,
                "advanced_count": sm.advanced_count,
                "historical_completion_rate": sm.historical_completion_rate,
            }
            for sm in funnel.stage_metrics
        ],
    }


@router.get(
    "/analytics/outcomes",
    response_model=None,
    summary="Get Stage Outcome Analytics",
    description="Get historical observed outcome rates per stage. Only available when sample size meets minimum threshold.",
)
def get_analytics_outcomes(
    workspace_id: str = Query(..., description="Workspace ID"),
    stage: Optional[str] = Query(None, description="Filter to a specific stage"),
    journey_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """GET /api/v1/journeys/analytics/outcomes"""
    outcomes = journey_api_v1.get_analytics_outcomes(workspace_id, stage, journey_type)
    if outcomes is None:
        raise HTTPException(status_code=404, detail="No outcome analytics found. Run POST /analytics first.")
    return {
        k: {
            "stage": v.stage,
            "outcome": v.outcome,
            "sample_size": v.sample_size,
            "observed_rate": v.observed_rate,
            "minimum_sample_met": v.minimum_sample_met,
            "confidence_interval_lower": v.confidence_interval_lower,
            "confidence_interval_upper": v.confidence_interval_upper,
            "data_status": v.data_status.value,
            "limitations": v.limitations,
        }
        for k, v in outcomes.items()
    }


@router.get(
    "/analytics/trends",
    response_model=None,
    summary="Get Journey Trends",
    description="Get time-series trend data for journey metrics over the observation window.",
)
def get_analytics_trends(
    workspace_id: str = Query(..., description="Workspace ID"),
    journey_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """GET /api/v1/journeys/analytics/trends"""
    trends = journey_api_v1.get_analytics_trends(workspace_id, journey_type)
    if trends is None:
        raise HTTPException(status_code=404, detail="No trend analytics found. Run POST /analytics first.")
    return {
        "granularity": trends.granularity.value,
        "metrics": trends.metrics,
        "total_periods": trends.total_periods,
        "data_points": [
            {
                "period_label": dp.period_label,
                "metric": dp.metric,
                "value": dp.value,
                "sample_size": dp.sample_size,
            }
            for dp in trends.data_points
        ],
    }


@router.delete(
    "/analytics/cache",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate Analytics Cache",
    description="Invalidate the analytics cache for a workspace, forcing recalculation on next request.",
)
def invalidate_analytics_cache(
    workspace_id: str = Query(..., description="Workspace ID"),
    journey_type: Optional[str] = Query(None),
) -> None:
    """DELETE /api/v1/journeys/analytics/cache"""
    journey_api_v1.invalidate_analytics_cache(workspace_id, journey_type)
