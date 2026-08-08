from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.domain.journey.models import JourneyEvidence, EvidenceType


@dataclass(frozen=True)
class EvidenceCollection:
    """Collection of evidence for journey progression."""
    
    evidence: List[JourneyEvidence] = field(default_factory=list)

    def add(self, new_evidence: JourneyEvidence) -> EvidenceCollection:
        """Return a new EvidenceCollection with the new evidence added."""
        return EvidenceCollection(evidence=self.evidence + [new_evidence])

    def filter_by_type(self, evidence_type: EvidenceType) -> EvidenceCollection:
        """Filter evidence by its type."""
        return EvidenceCollection(
            evidence=[e for e in self.evidence if e.evidence_type == evidence_type]
        )

    def filter_by_source(self, source: str) -> EvidenceCollection:
        """Filter evidence by its source."""
        return EvidenceCollection(
            evidence=[e for e in self.evidence if e.source == source]
        )

    def get_unique_source_ids(self) -> List[str]:
        """Get unique source IDs from all evidence."""
        return list(set(e.source_id for e in self.evidence if e.source_id))

    def compute_evidence_quality(self) -> float:
        """Compute an overall quality/confidence score based on the evidence."""
        if not self.evidence:
            return 0.0
        
        # Simple average of confidence scores
        total_confidence = sum(e.confidence for e in self.evidence)
        return total_confidence / len(self.evidence)
