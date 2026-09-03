from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_workspace
from app.api.dependencies.database import get_db_session
from app.domain.escalation import service

router = APIRouter(prefix="/escalations", tags=["Escalations"])

class ResolveEscalationRequest(BaseModel):
    resolved_by: str
    resolution_note: str

@router.get("", response_model=List[Dict[str, Any]])
async def list_pending_escalations(
    workspace_id: UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
):
    escalations = await service.get_pending_escalations(session, workspace_id)
    return [
        {
            "id": str(e.id),
            "customer_id": str(e.customer_id),
            "trigger_intent": e.trigger_intent,
            "status": e.status.value,
            "created_at": e.created_at.isoformat(),
        }
        for e in escalations
    ]

@router.post("/{escalation_id}/resolve", response_model=Dict[str, Any])
async def resolve_escalation(
    escalation_id: UUID,
    request: ResolveEscalationRequest,
    workspace_id: UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
):
    escalation = await service.resolve_escalation(
        session=session,
        escalation_id=escalation_id,
        workspace_id=workspace_id,
        resolved_by=request.resolved_by,
        resolution_note=request.resolution_note,
    )
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    # In a real app we'd commit the session here, but standard patterns
    # might rely on middleware. We'll explicitly commit.
    await session.commit()

    return {
        "id": str(escalation.id),
        "status": escalation.status.value,
        "resolved_at": escalation.resolved_at.isoformat(),
    }
