from typing import List, Tuple
from uuid import UUID

from .models import RecommendationCandidate

class RecommendationCandidateValidator:
    def validate(self, candidate: RecommendationCandidate, context_workspace_id: UUID) -> Tuple[bool, List[str]]:
        errors = []
        
        # 1. Check workspace isolation
        if candidate.workspace_id != context_workspace_id:
            errors.append(f"Candidate workspace_id {candidate.workspace_id} does not match context workspace_id {context_workspace_id}")
            
        if candidate.provenance.workspace_id != context_workspace_id:
            errors.append(f"Provenance workspace_id {candidate.provenance.workspace_id} does not match context workspace_id {context_workspace_id}")
            
        # 2. Valid confidence (0.0 to 1.0)
        # Using a direct attribute access, assuming RecommendationConfidence provides a numerical value
        conf_val = getattr(candidate.confidence, 'value', candidate.confidence)
        try:
            conf_float = float(conf_val)
            if not (0.0 <= conf_float <= 1.0):
                errors.append(f"Confidence value {conf_float} is out of bounds (0.0 to 1.0)")
        except (ValueError, TypeError):
            errors.append(f"Confidence value {conf_val} is not a valid float")
            
        # 3. Valid recommendation_type
        if candidate.recommendation_type is None:
            errors.append("Recommendation type cannot be None")
            
        # 4. Immutable evidence references workspace isolation
        for ref in candidate.evidence_references:
            if getattr(ref, 'workspace_id', context_workspace_id) != context_workspace_id:
                 errors.append("Evidence reference workspace_id does not match context workspace_id")
                 
        return len(errors) == 0, errors
