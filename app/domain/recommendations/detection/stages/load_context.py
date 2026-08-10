from typing import Any

class LoadContextStage:
    def __init__(self, context_provider: Any):
        """
        Args:
            context_provider: A RecommendationIntelligenceContextProvider instance
        """
        self.context_provider = context_provider

    def execute(self, target: Any, workspace: Any) -> Any:
        """
        Given a target and workspace, loads the upstream intelligence contexts
        via the ACL adapters to build the RecommendationDetectionContext.
        
        Args:
            target: The detection target
            workspace: The current workspace
            
        Returns:
            RecommendationDetectionContext: The loaded context
        """
        # Ensure deterministic and non-mutating execution
        context = self.context_provider.get_context(target=target, workspace=workspace)
        return context
