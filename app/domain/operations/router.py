from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.operations.schemas import (
    OperationalRequest, CreateActionRequest, ActionDTO, TransitionActionStatusRequest,
    OperationalContextDTO
)
from app.domain.operations.engine import OperationsEngine
from app.domain.operations.repository import ActionRepository
from app.domain.operations.exceptions import ActionConflictError, ActionNotFoundError
from app.domain.approval.engine import ApprovalEngine
from app.domain.action.engine import ActionEngine
from app.domain.integration.engine import IntegrationEngine
from app.domain.integration.credentials import JsonCredentialProvider
from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.orchestration.engine import ActionOrchestrationEngine
from app.domain.operations.orchestration.port import NoopExecutionPort
from app.domain.operations.orchestration.schemas import (
    OrchestrateActionRequest, 
    OrchestrationRunDTO,
    RetryOrchestrationRequest,
    CancelOrchestrationRequest
)
from app.domain.operations.orchestration.exceptions import (
    OrchestrationError,
    OrchestrationBlockedError,
    StalePinnedVersionError,
    RetryLimitExceededError,
    InvalidOrchestrationStateError
)
from app.domain.operations.query import OperationalQueryService

router = APIRouter(prefix="/operations", tags=["operations"])


def get_operations_engine(request: Request, db: AsyncSession = Depends(get_db)) -> OperationsEngine:
    cred_provider = JsonCredentialProvider()
    integration_engine = IntegrationEngine(db, cred_provider, request.app.state.event_bus)
    action_engine = ActionEngine(session=db, event_bus=request.app.state.event_bus, integration_engine=integration_engine)
    approval_engine = ApprovalEngine(session=db, event_bus=request.app.state.event_bus)
    repository = ActionRepository(db)
    planning_service = ActionPlanningService(session=db, repository=repository)
    orchestration_engine = ActionOrchestrationEngine(
        repository=repository,
        planning_service=planning_service,
        execution_port=NoopExecutionPort(),
        event_bus=request.app.state.event_bus,
    )
    return OperationsEngine(
        approval_engine=approval_engine,
        action_engine=action_engine,
        repository=repository,
        planning_service=planning_service,
        orchestration_engine=orchestration_engine,
        event_bus=request.app.state.event_bus
    )

def get_operational_query_service(db: AsyncSession = Depends(get_db)) -> OperationalQueryService:
    repository = ActionRepository(db)
    planning_service = ActionPlanningService(session=db, repository=repository)
    return OperationalQueryService(session=db, planning_service=planning_service)

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


@router.post("/workspace/{workspace_id}/actions", response_model=ActionDTO)
async def create_action(
    workspace_id: UUID,
    request: CreateActionRequest,
    engine: OperationsEngine = Depends(get_operations_engine)
):
    try:
        action = await engine.create_action(workspace_id, request)
        return action
    except ActionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{workspace_id}/actions", response_model=List[ActionDTO])
async def list_actions(
    workspace_id: UUID,
    limit: int = 50,
    offset: int = 0,
    engine: OperationsEngine = Depends(get_operations_engine)
):
    if not engine.repository:
        raise HTTPException(status_code=500, detail="Repository not initialized")
    actions = await engine.repository.list_actions(workspace_id, limit, offset)
    return actions


@router.get("/workspace/{workspace_id}/actions/{action_id}", response_model=ActionDTO)
async def get_action(
    workspace_id: UUID,
    action_id: UUID,
    engine: OperationsEngine = Depends(get_operations_engine)
):
    if not engine.repository:
        raise HTTPException(status_code=500, detail="Repository not initialized")
    action = await engine.repository.get_action(workspace_id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.patch("/workspace/{workspace_id}/actions/{action_id}", response_model=ActionDTO)
async def transition_action_status(
    workspace_id: UUID,
    action_id: UUID,
    request: TransitionActionStatusRequest,
    engine: OperationsEngine = Depends(get_operations_engine)
):
    try:
        action = await engine.transition_status(workspace_id, action_id, request)
        return action
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workspace/{workspace_id}/actions/{action_id}/orchestrate",
    response_model=OrchestrationRunDTO,
)
async def orchestrate_action(
    workspace_id: UUID,
    action_id: UUID,
    req: OrchestrateActionRequest,
    engine: OperationsEngine = Depends(get_operations_engine),
):
    """
    Phase 3.5 — Orchestrate an APPROVED Action.
    """
    try:
        if not engine.orchestration_engine:
            raise RuntimeError("OperationsEngine not initialized with orchestration_engine")
        return await engine.orchestration_engine.orchestrate(workspace_id, action_id, req)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StalePinnedVersionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except OrchestrationBlockedError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OrchestrationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workspace/{workspace_id}/actions/{action_id}/runs/{run_id}/retry",
    response_model=OrchestrationRunDTO,
)
async def retry_orchestration(
    workspace_id: UUID,
    action_id: UUID,
    run_id: UUID,
    req: RetryOrchestrationRequest,
    engine: OperationsEngine = Depends(get_operations_engine),
):
    try:
        if not engine.orchestration_engine:
            raise RuntimeError("OperationsEngine not initialized with orchestration_engine")
        return await engine.orchestration_engine.retry(workspace_id, action_id, run_id, req)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (StalePinnedVersionError, InvalidOrchestrationStateError, RetryLimitExceededError) as e:
        raise HTTPException(status_code=409, detail=str(e))
    except OrchestrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workspace/{workspace_id}/actions/{action_id}/runs/{run_id}/cancel",
    response_model=OrchestrationRunDTO,
)
async def cancel_orchestration(
    workspace_id: UUID,
    action_id: UUID,
    run_id: UUID,
    req: CancelOrchestrationRequest,
    engine: OperationsEngine = Depends(get_operations_engine),
):
    try:
        if not engine.orchestration_engine:
            raise RuntimeError("OperationsEngine not initialized with orchestration_engine")
        return await engine.orchestration_engine.cancel(workspace_id, action_id, run_id, req)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OrchestrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{workspace_id}/actions/{action_id}/context", response_model=OperationalContextDTO)
async def get_action_context(
    workspace_id: UUID,
    action_id: UUID,
    query_service: OperationalQueryService = Depends(get_operational_query_service),
):
    try:
        return await query_service.get_operational_context(workspace_id, action_id)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{workspace_id}/summary")
async def get_workspace_summary(
    workspace_id: UUID,
    query_service: OperationalQueryService = Depends(get_operational_query_service),
):
    try:
        return await query_service.get_workspace_operational_summary(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{workspace_id}/attention", response_model=List[OperationalContextDTO])
async def list_attention_actions(
    workspace_id: UUID,
    limit: int = 50,
    offset: int = 0,
    query_service: OperationalQueryService = Depends(get_operational_query_service),
):
    try:
        return await query_service.list_attention_actions(workspace_id, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

