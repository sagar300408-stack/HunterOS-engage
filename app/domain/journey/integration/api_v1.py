from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.domain.journey.integration.gateway import JourneyIntelligenceGateway

# Dummy schemas defined locally as per instructions
class JourneyContextDTO(BaseModel):
    journey_id: str
    foundation: Dict[str, Any]
    progression: Dict[str, Any]
    maturity: Dict[str, Any]
    analytics: Dict[str, Any]
    completeness_score: float
    generated_at: datetime

class StageContextDTO(BaseModel):
    progression: Dict[str, Any]

class MaturityContextDTO(BaseModel):
    maturity: Dict[str, Any]

class HistoryContextDTO(BaseModel):
    history: Dict[str, Any]

class TimelineContextDTO(BaseModel):
    timeline: Dict[str, Any]

class AnalyticsContextDTO(BaseModel):
    analytics: Dict[str, Any]

class ExecutiveContextDTO(BaseModel):
    executive_summary: Dict[str, Any]

class SalesContextDTO(BaseModel):
    sales_data: Dict[str, Any]

class OperationsContextDTO(BaseModel):
    operations_data: Dict[str, Any]

class AuditContextDTO(BaseModel):
    audit_data: Dict[str, Any]

class CustomContextDTO(BaseModel):
    custom_data: Dict[str, Any]

class JourneyIntegrationAPIv1:
    """
    Stable public contract for Phase 2.5 of the Journey Integration Layer.
    Maps internal domain models to Pydantic DTOs.
    """
    
    def __init__(self) -> None:
        self._gateway = JourneyIntelligenceGateway()

    def get_journey_context(self, journey_id: str) -> JourneyContextDTO:
        domain_model = self._gateway.get_journey_context(journey_id)
        return JourneyContextDTO(
            journey_id=domain_model.journey_id,
            foundation=domain_model.foundation,
            progression=domain_model.progression,
            maturity=domain_model.maturity,
            analytics=domain_model.analytics,
            completeness_score=domain_model.completeness_score,
            generated_at=domain_model.generated_at
        )

    def get_current_stage_context(self, journey_id: str) -> StageContextDTO:
        domain_data = self._gateway.get_current_stage_context(journey_id)
        return StageContextDTO(**domain_data)

    def get_maturity_context(self, journey_id: str) -> MaturityContextDTO:
        domain_data = self._gateway.get_maturity_context(journey_id)
        return MaturityContextDTO(**domain_data)

    def get_history_context(self, journey_id: str) -> HistoryContextDTO:
        domain_data = self._gateway.get_history_context(journey_id)
        return HistoryContextDTO(**domain_data)

    def get_timeline_context(self, journey_id: str) -> TimelineContextDTO:
        domain_data = self._gateway.get_timeline_context(journey_id)
        return TimelineContextDTO(**domain_data)

    def get_analytics_context(self, journey_id: str) -> AnalyticsContextDTO:
        domain_data = self._gateway.get_analytics_context(journey_id)
        return AnalyticsContextDTO(**domain_data)

    def get_executive_context(self, journey_id: str) -> ExecutiveContextDTO:
        domain_data = self._gateway.get_executive_context(journey_id)
        return ExecutiveContextDTO(**domain_data)

    def get_sales_context(self, journey_id: str) -> SalesContextDTO:
        domain_data = self._gateway.get_sales_context(journey_id)
        return SalesContextDTO(**domain_data)

    def get_operations_context(self, journey_id: str) -> OperationsContextDTO:
        domain_data = self._gateway.get_operations_context(journey_id)
        return OperationsContextDTO(**domain_data)

    def get_audit_context(self, journey_id: str) -> AuditContextDTO:
        domain_data = self._gateway.get_audit_context(journey_id)
        return AuditContextDTO(**domain_data)

    def get_custom_context(self, journey_id: str, options: Dict[str, Any]) -> CustomContextDTO:
        domain_data = self._gateway.get_custom_context(journey_id, options)
        return CustomContextDTO(**domain_data)

# Singleton instance
journey_integration_api_v1 = JourneyIntegrationAPIv1()
