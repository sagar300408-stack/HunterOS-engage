from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.approval.schemas import MakeDecisionRequest
from app.domain.operations.router import get_operations_engine
from app.domain.operations.engine import OperationsEngine

router = APIRouter(prefix="/approval", tags=["approval"])


@router.post("/{approval_id}/decision")
async def process_approval_decision(
    approval_id: UUID, 
    req: MakeDecisionRequest, 
    engine: OperationsEngine = Depends(get_operations_engine)
):
    """
    Process an approval decision. This goes through the Operations Engine 
    so it can orchestrate what happens next (e.g. trigger execution).
    """
    try:
        result = await engine.process_approval_decision(approval_id, req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
