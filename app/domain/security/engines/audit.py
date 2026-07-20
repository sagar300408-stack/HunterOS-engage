from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict
import uuid

from app.domain.security.models import AuditLog

class AuditEngine:
    """
    Handles creating immutable audit logs for sensitive operations.
    """
    
    @staticmethod
    def log_action(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: uuid.UUID = None,
        payload: Dict[str, Any] = None,
        ip_address: str = None
    ) -> AuditLog:
        
        audit_entry = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
            ip_address=ip_address
        )
        
        db.add(audit_entry)
        # Note: Do NOT await db.commit() here if part of a larger transaction,
        # but the caller must ensure commit happens.
        return audit_entry
