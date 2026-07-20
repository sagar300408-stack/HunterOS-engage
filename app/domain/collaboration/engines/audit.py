import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.domain.collaboration.models import (
    DecisionAuditLog, 
    DecisionExplanation,
    CollaborationTask
)
from app.domain.collaboration.repository import CollaborationRepository

class DecisionAuditEngine:
    """
    Persists every AI routing decision for executive traceability.
    """

    @classmethod
    async def log_decision(
        cls, 
        repo: CollaborationRepository, 
        task: CollaborationTask, 
        policy_version: int,
        execution_time_ms: float,
        inputs_snapshot: Dict[str, Any],
        explanation_text: str,
        confidence_factors: List[str],
        risk_factors: List[str]
    ) -> DecisionAuditLog:
        """
        Creates and persists a DecisionAuditLog and a DecisionExplanation.
        """
        
        audit_log = DecisionAuditLog(
            task_id=task.id,
            policy_version=policy_version,
            execution_time_ms=execution_time_ms,
            inputs_snapshot=inputs_snapshot
        )
        
        audit_log = await repo.save_audit_log(audit_log)
        
        # Explanation logic
        explanation = DecisionExplanation(
            audit_log_id=audit_log.id,
            reasoning_text=explanation_text,
            confidence_factors=confidence_factors,
            risk_factors=risk_factors
        )
        
        # In SQLAlchemy with async, if we just want to save it we can add to repo
        repo.session.add(explanation)
        await repo.session.commit()
        
        return audit_log
