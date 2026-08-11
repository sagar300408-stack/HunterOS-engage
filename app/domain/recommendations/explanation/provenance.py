from typing import Any, Dict, List
from .models import ExplanationEvidence, EvidenceReferenceType

class EvidenceCollector:
    def extract_evidence(self, candidate: Dict[str, Any], prioritization: Dict[str, Any]) -> List[ExplanationEvidence]:
        """Strictly extracts non-mutating evidence references from candidate and prioritization."""
        evidence_list = []
        if "metrics" in candidate:
            for k, v in candidate["metrics"].items():
                evidence_list.append(ExplanationEvidence(
                    reference_type=EvidenceReferenceType.METRIC,
                    reference_id=f"metric_{k}",
                    description=f"Candidate metric: {k}",
                    value=v,
                    impact="Neutral"
                ))
        return evidence_list
