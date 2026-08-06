"""
HunterOS Engage V1 - Intent History & Evolution FastAPI Router
REST endpoints for executing intent evolution, querying timelines, histories, event streams, and views.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.domain.intents.evolution.api import intent_evolution_api_v1
from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEventType,
)
from app.domain.intents.evolution.schemas import (
    EvolveIntentsRequest,
    IntentEvolutionAnalyticsDTO,
    IntentEvolutionEventDTO,
    IntentEvolutionResultDTO,
    IntentHistoryDTO,
    IntentTimelineDTO,
)
from app.domain.intents.evolution.strategies.registry import (
    default_evolution_strategy_registry,
)

router = APIRouter(prefix="/evolution", tags=["Intent Evolution"])


@router.post(
    "/evolve",
    summary="Evolve Entity Intents",
    response_model=IntentEvolutionResultDTO,
    status_code=status.HTTP_200_OK,
)
def evolve_intents(payload: EvolveIntentsRequest) -> Any:
    """Execute the deterministic 8-stage evolution pipeline for an entity."""
    try:
        res = intent_evolution_api_v1.evolve_intents(
            entity_id=payload.entity_id,
            current_conversation_id=payload.conversation_id,
            entity_type=payload.entity_type,
            workspace_id=payload.workspace_id,
            conversation_metadata=payload.conversation_metadata,
            persist=True,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent evolution failed: {str(e)}",
        )


@router.get(
    "/history/{intent_id}",
    summary="Get Intent History",
    response_model=IntentHistoryDTO,
)
def get_intent_history(intent_id: uuid.UUID) -> Any:
    """Fetch complete multi-conversation history for an intent."""
    history = intent_evolution_api_v1.get_intent_history(intent_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No history found for intent '{intent_id}'.",
        )
    return history


@router.get(
    "/timeline/{intent_id}",
    summary="Get Intent Timeline",
    response_model=IntentTimelineDTO,
)
def get_intent_timeline(intent_id: uuid.UUID) -> Any:
    """Fetch chronological timeline projection for an intent."""
    timeline = intent_evolution_api_v1.get_intent_timeline(intent_id)
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No timeline found for intent '{intent_id}'.",
        )
    return timeline


@router.get(
    "/entity/{entity_id}/timelines",
    summary="Get Entity Timelines",
    response_model=List[IntentTimelineDTO],
)
def get_entity_timelines(
    entity_id: str,
    entity_type: EntityType = EntityType.CUSTOMER,
    workspace_id: Optional[uuid.UUID] = None,
) -> Any:
    """Fetch all intent timelines for an entity."""
    return intent_evolution_api_v1.get_entity_timelines(
        entity_id=entity_id,
        entity_type=entity_type,
        workspace_id=workspace_id,
    )


@router.get(
    "/events",
    summary="Get Evolution Events",
    response_model=List[IntentEvolutionEventDTO],
)
def get_evolution_events(
    entity_id: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    workspace_id: Optional[uuid.UUID] = None,
    intent_id: Optional[uuid.UUID] = None,
    event_type: Optional[IntentEvolutionEventType] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> Any:
    """Query immutable evolution events with filtering."""
    return intent_evolution_api_v1.get_evolution_events(
        entity_id=entity_id,
        entity_type=entity_type,
        workspace_id=workspace_id,
        intent_id=intent_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/views/{entity_id}/{perspective}",
    summary="Get Perspective Evolution View",
    response_model=Dict[str, Any],
)
def get_evolution_view(
    entity_id: str,
    perspective: str,
    entity_type: EntityType = EntityType.CUSTOMER,
    workspace_id: Optional[uuid.UUID] = None,
) -> Any:
    """Project entity evolution state into a perspective view ('executive', 'sales', 'operations', 'audit')."""
    res = intent_evolution_api_v1.query.repository.get_latest_result_for_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        workspace_id=workspace_id,
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evolution result found for entity '{entity_id}'.",
        )
    try:
        return intent_evolution_api_v1.get_evolution_view(res, perspective)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/analytics/{entity_id}",
    summary="Get Descriptive Evolution Analytics",
    response_model=IntentEvolutionAnalyticsDTO,
)
def get_evolution_analytics(
    entity_id: str,
    entity_type: EntityType = EntityType.CUSTOMER,
    workspace_id: Optional[uuid.UUID] = None,
) -> Any:
    """Compute descriptive analytics for an entity."""
    return intent_evolution_api_v1.get_analytics(
        entity_id=entity_id,
        entity_type=entity_type,
        workspace_id=workspace_id,
    )


@router.get(
    "/strategies",
    summary="List Registered Evolution Strategies",
    response_model=List[Dict[str, Any]],
)
def list_strategies() -> Any:
    """List all registered evolution strategies."""
    strategies = default_evolution_strategy_registry.list_strategies()
    return [
        {
            "strategy_id": s.strategy_id,
            "strategy_version": s.strategy_version,
            "description": s.description,
        }
        for s in strategies
    ]
