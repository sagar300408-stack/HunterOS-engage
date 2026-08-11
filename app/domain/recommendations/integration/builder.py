from typing import Any, Dict, Optional
from datetime import datetime
import uuid

from .models import (
    RecommendationIntelligenceContext,
    ContextMetadata,
    ContextProvenance,
    ContextDiagnostics,
    ContextCompletenessReport,
    ContextCompletenessStatus
)
from .provenance import extract_lineage_metadata

class RecommendationContextBuilder:
    def __init__(self, identity_id: str):
        self.identity_id = identity_id
        self.candidate: Optional[Any] = None
        self.prioritization: Optional[Any] = None
        self.explanation: Optional[Any] = None
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.start_time = datetime.utcnow()

    def add_candidate(self, candidate: Any) -> 'RecommendationContextBuilder':
        if getattr(candidate, 'identity_id', None) != self.identity_id:
            self.errors.append("Candidate identity mismatch")
        else:
            self.candidate = candidate
        return self

    def add_prioritization(self, prioritization: Any) -> 'RecommendationContextBuilder':
        if getattr(prioritization, 'identity_id', None) != self.identity_id:
            self.errors.append("Prioritization identity mismatch")
        else:
            self.prioritization = prioritization
        return self

    def add_explanation(self, explanation: Any) -> 'RecommendationContextBuilder':
        if getattr(explanation, 'identity_id', None) != self.identity_id:
            self.errors.append("Explanation identity mismatch")
        else:
            self.explanation = explanation
        return self

    def _calculate_completeness(self) -> ContextCompletenessReport:
        present = []
        missing = []
        
        if self.candidate:
            present.append("candidate")
        else:
            missing.append("candidate")
            
        if self.prioritization:
            present.append("prioritization")
        else:
            missing.append("prioritization")
            
        if self.explanation:
            present.append("explanation")
        else:
            missing.append("explanation")
            
        if not missing:
            status = ContextCompletenessStatus.COMPLETE
        elif not present:
            status = ContextCompletenessStatus.INCOMPLETE
        else:
            status = ContextCompletenessStatus.PARTIAL
            
        if self.errors:
            status = ContextCompletenessStatus.DEGRADED

        return ContextCompletenessReport(
            status=status,
            missing_modules=missing,
            present_modules=present
        )

    def build(self) -> RecommendationIntelligenceContext:
        completeness = self._calculate_completeness()
        
        upstream = []
        if self.candidate: upstream.append(self.candidate)
        if self.prioritization: upstream.append(self.prioritization)
        if self.explanation: upstream.append(self.explanation)
        
        provenance = extract_lineage_metadata(str(uuid.uuid4()), upstream)
        
        execution_time = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        diagnostics = ContextDiagnostics(
            execution_time_ms=execution_time,
            warnings=self.warnings,
            errors=self.errors
        )
        
        metadata = ContextMetadata(
            version="1.0",
            generated_at=datetime.utcnow(),
            source_system="integration_builder"
        )
        
        candidate_data = getattr(self.candidate, 'data', None) if self.candidate else None
        prioritization_data = getattr(self.prioritization, 'data', None) if self.prioritization else None
        explanation_data = getattr(self.explanation, 'data', None) if self.explanation else None

        return RecommendationIntelligenceContext(
            identity_id=self.identity_id,
            metadata=metadata,
            provenance=provenance,
            diagnostics=diagnostics,
            completeness=completeness,
            candidate_data=candidate_data,
            prioritization_data=prioritization_data,
            explanation_data=explanation_data
        )
