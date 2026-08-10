from typing import Any

class NormalizeContextStage:
    def execute(self, context: Any) -> Any:
        """
        Validates that the loaded context has correct timestamps, non-null
        mandatory fields, and proper workspace boundaries for loaded evidence.
        
        Args:
            context: RecommendationDetectionContext
            
        Returns:
            RecommendationDetectionContext (normalized and validated)
            
        Raises:
            ValueError: If the context fails validation checks.
        """
        # Validate timestamp
        if not getattr(context, "timestamp", None):
            raise ValueError("Context validation failed: Missing or invalid timestamp.")
            
        # Validate workspace_id
        workspace_id = getattr(context, "workspace_id", None)
        if not workspace_id:
            raise ValueError("Context validation failed: Missing workspace_id.")
            
        # Validate evidence boundaries
        evidence_list = getattr(context, "evidence", [])
        for evidence in evidence_list:
            if getattr(evidence, "workspace_id", None) != workspace_id:
                raise ValueError(
                    f"Boundary validation failed: Evidence {getattr(evidence, 'id', 'unknown')} "
                    f"belongs to a different workspace."
                )
                
        return context
