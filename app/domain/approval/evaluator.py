from typing import Dict, Any, List

from app.domain.approval.models import ApprovalPolicy


class PolicyEvaluator:
    @staticmethod
    def evaluate(policy: ApprovalPolicy, context_data: Dict[str, Any]) -> bool:
        """
        Evaluates a policy's matching conditions against the provided context.
        context_data typically contains flat keys like 'risk', 'action_type', 'target_system', 'impact', etc.
        """
        if not policy.enabled:
            return False

        if not policy.matching_conditions:
            return True # No conditions means it matches everything (fallback policy)

        # Evaluate AND conditions
        for condition in policy.matching_conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            expected_value = condition.get("value")
            
            actual_value = context_data.get(field)
            
            if operator == "==":
                if actual_value != expected_value:
                    return False
            elif operator == "!=":
                if actual_value == expected_value:
                    return False
            elif operator == ">":
                if actual_value is None or float(actual_value) <= float(expected_value):
                    return False
            elif operator == "<":
                if actual_value is None or float(actual_value) >= float(expected_value):
                    return False
            # Can be expanded for IN, CONTAINS, etc.
            
        return True

    @staticmethod
    def evaluate_policies(policies: List[ApprovalPolicy], action: Any, context_data: Dict[str, Any]) -> "GovernanceEvaluationResult":
        """
        Evaluates an action against a list of policies and returns a structured GovernanceEvaluationResult.
        """
        from app.domain.approval.schemas import GovernanceEvaluationResult
        from datetime import datetime
        
        matching_policy = None
        for policy in policies:
            if PolicyEvaluator.evaluate(policy, context_data):
                matching_policy = policy
                break
                
        if not matching_policy:
            return GovernanceEvaluationResult(
                action_id=action.id,
                approval_required=False,
                reason="No approval policy matched the context.",
                evaluated_at=datetime.now(),
                action_version=getattr(action, 'revision_id', None),
                readiness_state=action.status
            )
            
        return GovernanceEvaluationResult(
            action_id=action.id,
            approval_required=True,
            policy_id=matching_policy.id,
            reason=f"Matched policy: {matching_policy.name}",
            evaluated_at=datetime.now(),
            action_version=getattr(action, 'revision_id', None),
            readiness_state=action.status
        )
