"""
HunterOS Engage V1 - Intent Intelligence FastAPI Router
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

REST Endpoints exposing Intent Intelligence Platform capabilities.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.domain.intents.integration.api_v1 import intent_intelligence_api_v1
from app.domain.intents.integration.models import CompositionProfileType
from app.domain.intents.integration.schemas import (
    AuditIntentContextDTO,
    CustomIntentContextDTO,
    DashboardIntentContextDTO,
    ExecutiveIntentContextDTO,
    ExecutiveIntentDTO,
    IntegrateIntentsRequest,
    IntentIntelligenceContextDTO,
    IntentIntelligenceResponse,
    OperationsIntentContextDTO,
    QueryIntentContextRequest,
    SalesIntentContextDTO,
    StandardAPIIntentContextDTO,
    StructuredIntentContextDTO,
)

router = APIRouter(prefix="/integration", tags=["Intent Intelligence Platform"])


@router.post(
    "/integrate",
    summary="Integrate Intent Intelligence Context",
    response_model=IntentIntelligenceResponse,
)
def integrate_intents(request: IntegrateIntentsRequest) -> IntentIntelligenceResponse:
    """Execute 7-stage deterministic integration pipeline across all Intent subsystems."""
    try:
        return intent_intelligence_api_v1.integrate_intents(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent integration failed: {str(e)}",
        )


@router.get(
    "/context/{conversation_id}",
    summary="Get Full Intent Intelligence Context",
    response_model=IntentIntelligenceContextDTO,
)
def get_full_context(
    conversation_id: str,
    profile: Optional[CompositionProfileType] = None,
) -> IntentIntelligenceContextDTO:
    """Retrieve full unified intent context for a given conversation ID."""
    ctx = intent_intelligence_api_v1.get_full_intent_context(conversation_id, profile=profile)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No integrated intent context found for conversation '{conversation_id}'.",
        )
    return ctx


@router.get(
    "/context/{conversation_id}/executive",
    summary="Get Executive Role Context",
    response_model=ExecutiveIntentContextDTO,
)
def get_executive_context(conversation_id: str) -> ExecutiveIntentContextDTO:
    """Retrieve strategic executive role perspective."""
    view = intent_intelligence_api_v1.get_executive_intent_context(conversation_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Executive context not found for conversation '{conversation_id}'.",
        )
    return view


@router.get(
    "/context/{conversation_id}/sales",
    summary="Get Sales Role Context",
    response_model=SalesIntentContextDTO,
)
def get_sales_context(conversation_id: str) -> SalesIntentContextDTO:
    """Retrieve sales and commercial role perspective."""
    view = intent_intelligence_api_v1.get_sales_intent_context(conversation_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales context not found for conversation '{conversation_id}'.",
        )
    return view


@router.get(
    "/context/{conversation_id}/operations",
    summary="Get Operations Role Context",
    response_model=OperationsIntentContextDTO,
)
def get_operations_context(conversation_id: str) -> OperationsIntentContextDTO:
    """Retrieve operational fulfillment role perspective."""
    view = intent_intelligence_api_v1.get_operations_intent_context(conversation_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operations context not found for conversation '{conversation_id}'.",
        )
    return view


@router.get(
    "/context/{conversation_id}/audit",
    summary="Get Audit Role Context",
    response_model=AuditIntentContextDTO,
)
def get_audit_context(conversation_id: str) -> AuditIntentContextDTO:
    """Retrieve complete audit trace perspective."""
    view = intent_intelligence_api_v1.get_audit_intent_context(conversation_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit context not found for conversation '{conversation_id}'.",
        )
    return view


@router.get(
    "/context/{conversation_id}/custom",
    summary="Get Custom Role Context",
    response_model=CustomIntentContextDTO,
)
def get_custom_context(conversation_id: str) -> CustomIntentContextDTO:
    """Retrieve custom filtered perspective."""
    view = intent_intelligence_api_v1.get_custom_intent_context(conversation_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom context not found for conversation '{conversation_id}'.",
        )
    return view


@router.get(
    "/export/dashboard/{conversation_id}",
    summary="Export Dashboard DTO",
    response_model=DashboardIntentContextDTO,
)
def export_dashboard(conversation_id: str) -> DashboardIntentContextDTO:
    """Export high-level UI dashboard projection."""
    dto = intent_intelligence_api_v1.export_dashboard(conversation_id)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context found for conversation '{conversation_id}'.",
        )
    return dto


@router.get(
    "/export/executive/{conversation_id}",
    summary="Export Executive DTO",
    response_model=ExecutiveIntentDTO,
)
def export_executive(conversation_id: str) -> ExecutiveIntentDTO:
    """Export C-suite condensed projection."""
    dto = intent_intelligence_api_v1.export_executive(conversation_id)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context found for conversation '{conversation_id}'.",
        )
    return dto


@router.get(
    "/export/structured/{conversation_id}",
    summary="Export Structured Engine DTO",
    response_model=StructuredIntentContextDTO,
)
def export_structured(conversation_id: str) -> StructuredIntentContextDTO:
    """Export structured downstream engine DTO."""
    dto = intent_intelligence_api_v1.export_structured(conversation_id)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context found for conversation '{conversation_id}'.",
        )
    return dto


@router.get(
    "/export/api/{conversation_id}",
    summary="Export Standard API DTO",
    response_model=StandardAPIIntentContextDTO,
)
def export_standard_api(conversation_id: str) -> StandardAPIIntentContextDTO:
    """Export clean standard API projection."""
    dto = intent_intelligence_api_v1.export_standard_api(conversation_id)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context found for conversation '{conversation_id}'.",
        )
    return dto


@router.post(
    "/query",
    summary="Query Intent Contexts",
    response_model=List[IntentIntelligenceContextDTO],
)
def query_contexts(request: QueryIntentContextRequest) -> List[IntentIntelligenceContextDTO]:
    """Query stored contexts matching specified filter criteria."""
    return intent_intelligence_api_v1.query_contexts(request)


@router.get(
    "/graph/{conversation_id}/lineage/{intent_id}",
    summary="Get Intent Lineage Across Subsystems",
    response_model=List[Dict[str, Any]],
)
def get_intent_lineage(conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
    """Retrieve full cross-subsystem lineage path for a given intent ID."""
    return intent_intelligence_api_v1.get_intent_lineage(conversation_id, intent_id)


@router.get(
    "/graph/{conversation_id}/conflicts/{intent_id}",
    summary="Get Intent Conflicts",
    response_model=List[Dict[str, Any]],
)
def get_intent_conflicts(conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
    """Retrieve all conflicting intent nodes for a given intent ID."""
    return intent_intelligence_api_v1.get_intent_conflicts(conversation_id, intent_id)


@router.get(
    "/graph/{conversation_id}/dependencies/{intent_id}",
    summary="Get Intent Dependencies",
    response_model=List[Dict[str, Any]],
)
def get_intent_dependencies(conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
    """Retrieve all prerequisite dependency nodes for a given intent ID."""
    return intent_intelligence_api_v1.get_intent_dependencies(conversation_id, intent_id)


@router.get(
    "/profiles",
    summary="List Registered Composition Profiles",
    response_model=List[Dict[str, Any]],
)
def list_profiles() -> List[Dict[str, Any]]:
    """List all registered declarative composition profiles."""
    return intent_intelligence_api_v1.list_profiles()


@router.get(
    "/plugins",
    summary="List Registered Extension Plugins",
    response_model=List[Dict[str, Any]],
)
def list_plugins() -> List[Dict[str, Any]]:
    """List all registered platform extension plugins."""
    return intent_intelligence_api_v1.list_plugins()
