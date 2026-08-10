from typing import List
from .models import RecommendationPrioritizationResult, PriorityFactor
from .context import RecommendationPrioritizationContext

class RecommendationPrioritizationValidator:
    
    @staticmethod
    def validate(result: RecommendationPrioritizationResult, context: RecommendationPrioritizationContext) -> bool:
        RecommendationPrioritizationValidator._check_workspace_isolation(result, context)
        RecommendationPrioritizationValidator._check_score_bounds(result)
        RecommendationPrioritizationValidator._check_evidence_integrity(result)
        RecommendationPrioritizationValidator._check_no_candidate_mutation(result, context)
        return True

    @staticmethod
    def _check_workspace_isolation(result: RecommendationPrioritizationResult, context: RecommendationPrioritizationContext):
        if result.workspace_id != context.workspace_id:
            raise ValueError("Workspace Isolation failed: Result workspace_id does not match context")
        for rec in result.recommendations:
            if rec.candidate.workspace_id != context.workspace_id:
                raise ValueError("Workspace Isolation failed: Candidate workspace_id does not match context")

    @staticmethod
    def _check_score_bounds(result: RecommendationPrioritizationResult):
        for rec in result.recommendations:
            if not (0 <= rec.assessment.score.normalized_score <= 100):
                raise ValueError("Score Bounds failed: normalized_score must be between 0 and 100")
            for factor in rec.assessment.score.factors:
                if not (0 <= factor.score <= 100):
                    raise ValueError("Score Bounds failed: factor score must be between 0 and 100")

    @staticmethod
    def _check_evidence_integrity(result: RecommendationPrioritizationResult):
        for rec in result.recommendations:
            for factor in rec.assessment.score.factors:
                if not factor.evidence:
                    raise ValueError("Evidence Integrity failed: evidence cannot be empty")

    @staticmethod
    def _check_no_candidate_mutation(result: RecommendationPrioritizationResult, context: RecommendationPrioritizationContext):
        context_candidates = {c.candidate_id: c for c in context.candidate_recommendations}
        for rec in result.recommendations:
            if rec.candidate.candidate_id not in context_candidates:
                raise ValueError("No Recommendation Creation failed: New candidate created")
            original = context_candidates[rec.candidate.candidate_id]
            if rec.candidate != original:
                raise ValueError("No Candidate Mutation failed: Candidate was altered")
