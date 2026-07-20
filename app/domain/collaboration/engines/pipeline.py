import time
from typing import Dict, Any, Optional

from app.domain.collaboration.repository import CollaborationRepository
from app.domain.collaboration.models import (
    ActionableIntent, 
    CollaborationTask, 
    TaskStatus,
    AutonomyLevel
)

from app.domain.collaboration.engines.intent import IntentEngine
from app.domain.collaboration.engines.exceptions import ExceptionHandlingEngine
from app.domain.collaboration.engines.context import OperationalContextEngine
from app.domain.collaboration.engines.confidence import AIConfidenceEngine
from app.domain.collaboration.engines.risk import RiskAssessmentEngine
from app.domain.collaboration.engines.autonomy import AdaptiveAutonomyEngine
from app.domain.collaboration.engines.ownership import TaskOwnershipEngine
from app.domain.collaboration.engines.audit import DecisionAuditEngine

class DecisionRouter:
    """
    The main orchestrator for the Human-AI Collaboration Layer.
    Flows through the 8 foundational routing engines.
    """

    def __init__(self, repo: CollaborationRepository):
        self.repo = repo

    async def route_event(self, workspace_id: str, event_type: str, payload: Dict[str, Any]) -> Optional[CollaborationTask]:
        start_time = time.time()
        
        # 1. Intent Engine
        intent = IntentEngine.evaluate(workspace_id, event_type, payload)
        if not intent:
            return None # Not an actionable intent
            
        intent = await self.repo.create_intent(intent)
        
        # 2. Exception Handling Engine
        has_exception, exception_reasons = ExceptionHandlingEngine.evaluate(intent)
        
        # 3. Operational Context Engine
        enriched_context, context_factors = OperationalContextEngine.evaluate(intent)
        
        # 4. AI Confidence Engine
        confidence, confidence_factors = AIConfidenceEngine.evaluate(intent, enriched_context)
        
        # 5. Risk Assessment Engine
        risk_level, risk_factors = RiskAssessmentEngine.evaluate(intent, enriched_context)
        
        # 6. Adaptive Autonomy Engine
        base_autonomy, policy_version, autonomy_factors = await AdaptiveAutonomyEngine.evaluate(
            self.repo, workspace_id, intent.intent_type
        )
        
        # 7. Task Ownership Engine
        final_autonomy, ownership_reasons = TaskOwnershipEngine.evaluate(
            has_exception=has_exception,
            base_autonomy=base_autonomy,
            risk_level=risk_level,
            confidence=confidence
        )
        
        # Create Task
        task = CollaborationTask(
            workspace_id=workspace_id,
            intent_id=intent.id,
            status=TaskStatus.PENDING,
            ownership=final_autonomy,
            risk_level=risk_level,
            confidence_score=confidence
        )
        task = await self.repo.create_task(task)
        
        # 8. Decision Audit Engine
        execution_time_ms = (time.time() - start_time) * 1000
        
        inputs_snapshot = {
            "has_exception": has_exception,
            "exception_reasons": exception_reasons,
            "context_factors": context_factors,
            "base_autonomy": base_autonomy.value
        }
        
        explanation_text = " -> ".join(ownership_reasons)
        if has_exception:
            explanation_text = f"Exceptions: {', '.join(exception_reasons)}. " + explanation_text
            
        await DecisionAuditEngine.log_decision(
            repo=self.repo,
            task=task,
            policy_version=policy_version,
            execution_time_ms=execution_time_ms,
            inputs_snapshot=inputs_snapshot,
            explanation_text=explanation_text,
            confidence_factors=confidence_factors,
            risk_factors=risk_factors
        )
        
        # Trigger Execution Queue (e.g. DelegationEngine, ApprovalFramework)
        # This is where the task actually gets pushed to a human's queue or AI worker queue.
        # For this milestone, we mark it awaiting appropriately.
        
        if final_autonomy in (AutonomyLevel.HUMAN_REVIEW, AutonomyLevel.SHARED):
             task.status = TaskStatus.WAITING_APPROVAL
             # The Human Approval Framework would attach Approval chains here
        elif final_autonomy == AutonomyLevel.AI_OWNED:
             # The Delegation Engine assigns it to the best AI Agent
             pass
        elif final_autonomy == AutonomyLevel.HUMAN_OWNED:
             # The Delegation Engine assigns it to the best Human worker
             pass
             
        await self.repo.session.commit()
        await self.repo.session.refresh(task)
        
        return task
