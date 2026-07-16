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
