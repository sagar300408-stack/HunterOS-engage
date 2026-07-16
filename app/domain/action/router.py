from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.action.repository import ActionRepository
from app.domain.action.engine import ActionEngine
from app.domain.action.schemas import ActionExecutionResponse, SubmitActionRequest
from app.domain.integration.router import get_integration_engine

router = APIRouter(prefix="/action", tags=["action"])


def get_action_engine(request: Request, db: AsyncSession = Depends(get_db)) -> ActionEngine:
    integration_engine = get_integration_engine(request, db)
    return ActionEngine(session=db, event_bus=request.app.state.event_bus, integration_engine=integration_engine)


@router.post("/workspace/{workspace_id}/submit", response_model=ActionExecutionResponse)
async def submit_action(
    workspace_id: UUID, 
    req: SubmitActionRequest, 
    engine: ActionEngine = Depends(get_action_engine)
):
    """
    Submit a new operational action for background execution.
    """
    try:
        action = await engine.submit_action(workspace_id, req)
        return action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{action_id}", response_model=ActionExecutionResponse)
async def get_action_status(action_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get the status of an executed action.
    """
    repo = ActionRepository(db)
    action = await repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/cancel")
async def cancel_action(action_id: UUID, engine: ActionEngine = Depends(get_action_engine)):
    """
    (To be fully implemented) Cancels a PENDING or VALIDATING action.
    """
    raise HTTPException(status_code=501, detail="Cancel not yet implemented")


@router.post("/{action_id}/retry")
async def retry_action(action_id: UUID, engine: ActionEngine = Depends(get_action_engine)):
    """
    (To be fully implemented) Retries a FAILED action.
    """
    raise HTTPException(status_code=501, detail="Retry not yet implemented")
