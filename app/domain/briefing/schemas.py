from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.briefing.models import BriefingPeriod


class BriefingSnapshotResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    
    template_name: str
    period: str
    
    executive_summary: str
    
    kpi_summary: List[Dict[str, Any]]
    health_summary: List[Dict[str, Any]]
    key_insights: List[Dict[str, Any]]
    priority_recommendations: List[Dict[str, Any]]
    critical_risks: List[Dict[str, Any]]
    business_opportunities: List[Dict[str, Any]]
    
    supporting_references: List[str]
    confidence: float
    
    generated_at: datetime

    class Config:
        from_attributes = True


class BriefingCalculationResult(BaseModel):
    executive_summary: str
    kpi_summary: List[Dict[str, Any]] = []
    health_summary: List[Dict[str, Any]] = []
    key_insights: List[Dict[str, Any]] = []
    priority_recommendations: List[Dict[str, Any]] = []
    critical_risks: List[Dict[str, Any]] = []
    business_opportunities: List[Dict[str, Any]] = []
    
    supporting_references: List[str] = []
    confidence: float = 0.0
