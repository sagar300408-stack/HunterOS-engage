from typing import Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.action.schemas import SubmitActionRequest
from app.domain.approval.schemas import ApprovalContext

class OperationalRequest(BaseModel):
    # What to do
    connector_id: str
    target_system: str
    action_type: str
    parameters: Dict[str, Any]
    idempotency_key: str
    
    # Metadata
    requested_by: str
    correlation_id: Optional[UUID] = None
    priority: str = "normal"
    
    # Governance Context
    approval_context: Optional[ApprovalContext] = None
    
    def to_submit_action_request(self) -> SubmitActionRequest:
        return SubmitActionRequest(
            connector_id=self.connector_id,
            target_system=self.target_system,
            action_type=self.action_type,
            parameters=self.parameters,
            idempotency_key=self.idempotency_key,
            correlation_id=self.correlation_id,
            priority=self.priority,
            requested_by=self.requested_by
        )
