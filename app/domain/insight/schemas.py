from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.insight.models import InsightCategory, InsightSeverity, InsightImpact, InsightLifecycle


class EvidenceNode(BaseModel):
    id: str  # Unique identifier within the graph
    label: str
    node_type: str  # e.g., KPI, HEALTH, TIMELINE_EVENT, ANALYTICS, ACTION
    data: Dict[str, Any]


class EvidenceEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: str  # e.g., CAUSES, CORRELATES_WITH, CONTRIBUTES_TO


class EvidenceGraph(BaseModel):
    nodes: List[EvidenceNode]
    edges: List[EvidenceEdge]
    version: str = "1.0"


class InsightGeneratorDefinition(BaseModel):
    name: str
    version: str = "1.0"
    description: str


class InsightSnapshotResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    target_type: str
    target_id: UUID
    
    title: str
    summary: str
    
    category: str
    severity: str
    impact: str
    
    lifecycle_status: str
    
    confidence: float
    
    evidence_graph: Dict[str, Any]
    graph_version: str
    
    related_kpis: List[str]
    related_health_objects: List[str]
    related_timeline_events: List[str]
    
    generator_name: str
    generator_version: str
    trigger_source: str
    
    generated_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class InsightCalculationResult(BaseModel):
    title: str
    summary: str
    category: InsightCategory
    severity: InsightSeverity
    impact: InsightImpact
    confidence: float
    evidence_graph: EvidenceGraph
    related_kpis: List[str] = []
    related_health_objects: List[str] = []
    related_timeline_events: List[str] = []
