from __future__ import annotations

from typing import Any, List, Dict
from app.domain.journey.integration.models import JourneyIntelligenceContext

class JourneyContextValidator:
    """Validates properties of JourneyIntelligenceContext."""
    
    def validate(self, context: JourneyIntelligenceContext) -> Dict[str, Any]:
        """
        Run all validations and return validation errors/warnings.
        Never infers missing data.
        """
        errors = []
        warnings = []
        
        errors.extend(self._validate_workspace_isolation(context))
        errors.extend(self._validate_journey_identity_consistency(context))
        errors.extend(self._validate_entity_identity_consistency(context))
        errors.extend(self._validate_definition_compatibility(context))
        errors.extend(self._validate_schema_versions(context))
        errors.extend(self._validate_block_consistency(context))
        errors.extend(self._validate_timeline_consistency(context))
        errors.extend(self._validate_stage_consistency(context))
        errors.extend(self._validate_maturity_consistency(context))
        errors.extend(self._validate_analytics_consistency(context))
        errors.extend(self._validate_historical_outcome_consistency(context))
        errors.extend(self._validate_provenance_completeness(context))
        
        return {"errors": errors, "warnings": warnings}

    def _validate_workspace_isolation(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_journey_identity_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_entity_identity_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_definition_compatibility(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_schema_versions(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_block_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_timeline_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_stage_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_maturity_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_analytics_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_historical_outcome_consistency(self, context: JourneyIntelligenceContext) -> List[str]:
        return []

    def _validate_provenance_completeness(self, context: JourneyIntelligenceContext) -> List[str]:
        return []
