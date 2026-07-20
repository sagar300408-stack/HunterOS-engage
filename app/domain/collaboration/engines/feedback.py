import uuid
from typing import List, Dict, Any
from app.domain.collaboration.models import TaskFeedback, CollaborationTask, LearningRule, LearningRuleStatus
from app.domain.collaboration.repository import CollaborationRepository

class HumanFeedbackEngine:
    """
    Processes employee ratings and overrides.
    """

    @classmethod
    async def process_feedback(
        cls, 
        repo: CollaborationRepository, 
        feedback: TaskFeedback
    ) -> TaskFeedback:
        
        feedback = await repo.save_feedback(feedback)
        
        # If it was an override, trigger learning engine
        if feedback.is_override:
            await LearningEngine.evaluate_override(repo, feedback)
            
        return feedback


class LearningEngine:
    """
    Analyzes overrides. If the same override happens multiple times, proposes a LearningRule.
    """
    
    OVERRIDE_THRESHOLD = 3

    @classmethod
    async def evaluate_override(cls, repo: CollaborationRepository, feedback: TaskFeedback):
        """
        Naive heuristic: if the same intent type gets overriden with similar details X times, draft a rule.
        """
        task = await repo.get_task_by_id(feedback.task_id)
        if not task:
            return
            
        intent_type = task.intent.intent_type
        
        # In a real implementation, we would query the DB for similar overrides.
        # For Milestone 2, we just create a Draft Learning Rule to demonstrate the architecture.
        
        suggested_policy = {
            "autonomy_level": "HUMAN_OWNED"
        }
        
        rule = LearningRule(
            workspace_id=task.workspace_id,
            intent_type=intent_type,
            suggested_policy_change=suggested_policy,
            pattern_description=f"Detected pattern from human override on {intent_type}",
            occurrences=1,
            status=LearningRuleStatus.DRAFT
        )
        
        repo.session.add(rule)
        await repo.session.commit()
