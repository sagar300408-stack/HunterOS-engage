from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.operations.schemas import OperationalRequest
from app.domain.operations.engine import OperationsEngine
from app.domain.approval.engine import ApprovalEngine
from app.domain.action.engine import ActionEngine
from app.domain.integration.router import get_integration_engine

router = APIRouter(prefix="/operations", tags=["operations"])


def get_operations_engine(request: Request, db: AsyncSession = Depends(get_db)) -> OperationsEngine:
    integration_engine = get_integration_engine(request, db)
    action_engine = ActionEngine(session=db, event_bus=request.app.state.event_bus, integration_engine=integration_engine)
    approval_engine = ApprovalEngine(session=db, event_bus=request.app.state.event_bus)
    return OperationsEngine(approval_engine=approval_engine, action_engine=action_engine)


@router.post("/workspace/{workspace_id}/submit")
async def submit_operational_request(
    workspace_id: UUID, 
    req: OperationalRequest, 
    engine: OperationsEngine = Depends(get_operations_engine)
):
    """
    Submit a new operational request. The Operations Engine will determine if
    it requires approval or if it can be immediately executed.
    """
    try:
        result = await engine.submit_request(workspace_id, req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
