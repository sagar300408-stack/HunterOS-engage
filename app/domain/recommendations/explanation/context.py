from typing import Any, Dict
from dataclasses import dataclass
from .models import ExplanationProvenance

@dataclass(frozen=True)
class RecommendationExplanationContext:
    workspace_id: str
    recommendation: Dict[str, Any]
    prioritization: Dict[str, Any]
    candidate: Dict[str, Any]
    evidence: Dict[str, Any]
    configuration: Dict[str, Any]
    provenance: ExplanationProvenance

    @property
    def get_workspace_id(self) -> str:
        return self.workspace_id

    @property
    def get_recommendation(self) -> Dict[str, Any]:
        return self.recommendation

    @property
    def get_prioritization(self) -> Dict[str, Any]:
        return self.prioritization

    @property
    def get_candidate(self) -> Dict[str, Any]:
        return self.candidate

    @property
    def get_evidence(self) -> Dict[str, Any]:
        return self.evidence

    @property
    def get_configuration(self) -> Dict[str, Any]:
        return self.configuration

    @property
    def get_provenance(self) -> ExplanationProvenance:
        return self.provenance
