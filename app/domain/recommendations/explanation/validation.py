from .context import RecommendationExplanationContext

class RecommendationExplanationValidator:
    def validate(self, context: RecommendationExplanationContext) -> bool:
        if not context.workspace_id:
            raise ValueError("Workspace Isolation Error: No workspace_id provided.")
        
        if "recalculated" in str(context.prioritization).lower():
             raise ValueError("Validation Error: Priority recalculation is strictly prohibited during explanation.")
             
        if context.configuration.get("use_llm", False):
            raise ValueError("Validation Error: LLM Invocation is prohibited in this core framework.")

        if "execute_action" in str(context.configuration).lower():
            raise ValueError("Validation Error: Action Execution is prohibited.")
            
        return True
