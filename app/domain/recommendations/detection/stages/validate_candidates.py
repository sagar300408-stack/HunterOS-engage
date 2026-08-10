from typing import Any, List

class ValidateCandidatesStage:
    def __init__(self, validator: Any):
        """
        Args:
            validator: A RecommendationCandidateValidator instance
        """
        self.validator = validator

    def execute(self, candidates: List[Any], diagnostics: Any) -> List[Any]:
        """
        Runs each candidate through RecommendationCandidateValidator.
        Rejects invalid ones. Records validated/rejected into diagnostics.
        
        Args:
            candidates: List of RecommendationCandidate objects
            diagnostics: DetectionDiagnostics instance
            
        Returns:
            List[RecommendationCandidate]: The valid candidates
        """
        valid_candidates = []
        
        for candidate in candidates:
            if self.validator.validate(candidate):
                valid_candidates.append(candidate)
            else:
                if hasattr(diagnostics, "candidates_rejected"):
                    diagnostics.candidates_rejected += 1
                    
        if hasattr(diagnostics, "candidates_validated"):
            diagnostics.candidates_validated += len(valid_candidates)
            
        return valid_candidates
