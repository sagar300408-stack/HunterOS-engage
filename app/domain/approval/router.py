from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.approval.schemas import MakeDecisionRequest
from app.domain.operations.router import get_operations_engine
from app.domain.operations.engine import OperationsEngine
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User

router = APIRouter(prefix="/approval", tags=["approval"])


@router.post("/{approval_id}/decision")
async def process_approval_decision(
    approval_id: UUID, 
    req: MakeDecisionRequest, 
    engine: OperationsEngine = Depends(get_operations_engine),
    current_user: User = Depends(get_current_user),
):
    """
    Process an approval decision. The authenticated actor identity is derived
    from the JWT token — not the request body — to enforce Segregation of Duties.
    """
    try:
        # authenticated_actor_id is always derived from the verified JWT, never trusting req.approver_id
        result = await engine.process_approval_decision(approval_id, req, authenticated_actor_id=str(current_user.id))
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

