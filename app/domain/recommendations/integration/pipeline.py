from typing import Any, Dict, Optional
from .strategies.base import RecommendationCompositionStrategy
from .strategies.full import FullCompositionStrategy

class RecommendationIntegrationPipeline:
    """
    Deterministic pipeline for assembling and integrating recommendation artifacts.
    """
    def __init__(self, default_strategy: Optional[RecommendationCompositionStrategy] = None):
        self.default_strategy = default_strategy or FullCompositionStrategy()

    def execute(
        self,
        detection_ref: str,
        prioritization_ref: str,
        explanation_ref: str,
        strategy: Optional[RecommendationCompositionStrategy] = None
    ) -> Dict[str, Any]:
        """
        Executes the 7-stage deterministic integration pipeline.
        """
        # Stage 1: Load Artifacts
        artifacts = self._stage_1_load_artifacts(detection_ref, prioritization_ref, explanation_ref)
        
        # Stage 2: Validate Inputs
        self._stage_2_validate_inputs(artifacts)
        
        # Stage 3: Normalize Artifacts
        normalized = self._stage_3_normalize_artifacts(artifacts)
        
        # Stage 4: Apply Composition Strategy
        composition_strategy = strategy or self.default_strategy
        composition = self._stage_4_apply_composition_strategy(composition_strategy, normalized)
        
        # Stage 5: Assemble Unified Context
        unified_context = self._stage_5_assemble_unified_context(composition)
        
        # Stage 6: Validate Final Context (Zero-Trust)
        self._stage_6_validate_final_context(unified_context)
        
        # Stage 7: Generate Integration Result
        return self._stage_7_generate_integration_result(unified_context)

    def _stage_1_load_artifacts(self, detection_ref: str, prioritization_ref: str, explanation_ref: str) -> Dict[str, Any]:
        # In a real implementation, this would fetch from a repository or artifact store
        return {
            "detection": {"ref": detection_ref, "data": "dummy_detection"},
            "prioritization": {"ref": prioritization_ref, "data": "dummy_prioritization"},
            "explanation": {"ref": explanation_ref, "data": "dummy_explanation"}
        }

    def _stage_2_validate_inputs(self, artifacts: Dict[str, Any]) -> None:
        if not artifacts.get("detection"):
            raise ValueError("Detection artifact is required.")

    def _stage_3_normalize_artifacts(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize structures
        return artifacts

    def _stage_4_apply_composition_strategy(
        self, 
        strategy: RecommendationCompositionStrategy, 
        normalized_artifacts: Dict[str, Any]
    ) -> Dict[str, Any]:
        return strategy.assemble(
            detection_artifact=normalized_artifacts.get("detection"),
            prioritization_artifact=normalized_artifacts.get("prioritization"),
            explanation_artifact=normalized_artifacts.get("explanation")
        )

    def _stage_5_assemble_unified_context(self, composition: Dict[str, Any]) -> Dict[str, Any]:
        # Assemble into a unified structure
        return {
            "metadata": {"version": "1.0", "assembled_at": "now"},
            "content": composition
        }

    def _stage_6_validate_final_context(self, unified_context: Dict[str, Any]) -> None:
        # Zero-Trust validation
        if "content" not in unified_context:
            raise ValueError("Unified context must contain content.")

    def _stage_7_generate_integration_result(self, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "result": unified_context
        }
