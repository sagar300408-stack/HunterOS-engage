from typing import Optional
from uuid import UUID

from app.domain.insight.generators.base import BaseInsightGenerator
from app.domain.insight.schemas import (
    InsightGeneratorDefinition, InsightCalculationResult, 
    EvidenceGraph, EvidenceNode, EvidenceEdge,
    InsightCategory, InsightSeverity, InsightImpact
)
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository
from app.domain.health.models import HealthTrend, HealthStatus


class EngagementImprovementGenerator(BaseInsightGenerator):
    @property
    def definition(self) -> InsightGeneratorDefinition:
        return InsightGeneratorDefinition(
            name="EngagementImprovementGenerator",
            version="1.0",
            description="Detects when customer engagement improves due to reply rate increases."
        )

    async def analyze(self, kpi_repo: KpiRepository, health_repo: HealthRepository, target_type: str, target_id: UUID) -> Optional[InsightCalculationResult]:
        # 1. Look for improving Customer Engagement Health
        health_snapshots = await health_repo.get_latest_snapshots(target_type, target_id)
        engagement_health = next((h for h in health_snapshots if h.health_name == "customer_engagement_health"), None)
        
        if not engagement_health:
            return None
            
        # 2. Check if trend is UP
        if engagement_health.trend != HealthTrend.UP.value:
            return None
            
        # 3. Look for the underlying KPI that drove it
        kpi_snapshots = await kpi_repo.get_latest_snapshots(target_type, target_id)
        reply_rate_kpi = next((k for k in kpi_snapshots if k.kpi_name == "reply_rate"), None)
        
        if not reply_rate_kpi or reply_rate_kpi.percentage_change is None or reply_rate_kpi.percentage_change <= 0:
            return None

        # 4. Construct Evidence Graph
        health_node = EvidenceNode(
            id=f"health_{engagement_health.id}",
            label="Customer Engagement Health",
            node_type="HEALTH",
            data={"status": engagement_health.status, "trend": engagement_health.trend}
        )
        
        kpi_node = EvidenceNode(
            id=f"kpi_{reply_rate_kpi.id}",
            label="Reply Rate KPI",
            node_type="KPI",
            data={"current_value": reply_rate_kpi.current_value, "percentage_change": reply_rate_kpi.percentage_change}
        )
        
        edge = EvidenceEdge(
            source_id=kpi_node.id,
            target_id=health_node.id,
            relationship="DRIVES_IMPROVEMENT_IN"
        )
        
        graph = EvidenceGraph(
            nodes=[health_node, kpi_node],
            edges=[edge],
            version="1.0"
        )
        
        # 5. Derive confidence based on evidence quality
        # High confidence if we have both nodes and positive change
        confidence = 0.9 if reply_rate_kpi.percentage_change > 5.0 else 0.7
        
        return InsightCalculationResult(
            title="Customer Engagement Improved",
            summary=f"Customer engagement health improved to {engagement_health.status.upper()} driven by a {reply_rate_kpi.percentage_change:.1f}% increase in reply rates.",
            category=InsightCategory.PERFORMANCE_IMPROVEMENT,
            severity=InsightSeverity.INFO,
            impact=InsightImpact.MEDIUM,
            confidence=confidence,
            evidence_graph=graph,
            related_kpis=[reply_rate_kpi.kpi_name],
            related_health_objects=[engagement_health.health_name]
        )


class SalesPipelineGenerator(BaseInsightGenerator):
    @property
    def definition(self) -> InsightGeneratorDefinition:
        return InsightGeneratorDefinition(
            name="SalesPipelineGenerator",
            version="1.0",
            description="Detects risks or opportunities in the sales pipeline."
        )

    async def analyze(self, kpi_repo: KpiRepository, health_repo: HealthRepository, target_type: str, target_id: UUID) -> Optional[InsightCalculationResult]:
        health_snapshots = await health_repo.get_latest_snapshots(target_type, target_id)
        sales_health = next((h for h in health_snapshots if h.health_name == "sales_health"), None)
        
        if not sales_health:
            return None
            
        if sales_health.status in [HealthStatus.WARNING.value, HealthStatus.CRITICAL.value]:
            kpi_snapshots = await kpi_repo.get_latest_snapshots(target_type, target_id)
            conversion_kpi = next((k for k in kpi_snapshots if k.kpi_name == "meeting_conversion_rate"), None)
            
            if not conversion_kpi:
                return None
                
            health_node = EvidenceNode(
                id=f"health_{sales_health.id}",
                label="Sales Health",
                node_type="HEALTH",
                data={"status": sales_health.status, "trend": sales_health.trend}
            )
            
            kpi_node = EvidenceNode(
                id=f"kpi_{conversion_kpi.id}",
                label="Meeting Conversion KPI",
                node_type="KPI",
                data={"current_value": conversion_kpi.current_value}
            )
            
            edge = EvidenceEdge(
                source_id=kpi_node.id,
                target_id=health_node.id,
                relationship="CAUSES_RISK_IN"
            )
            
            graph = EvidenceGraph(
                nodes=[health_node, kpi_node],
                edges=[edge],
                version="1.0"
            )
            
            return InsightCalculationResult(
                title="Sales Pipeline Risk Detected",
                summary=f"Sales health is currently {sales_health.status.upper()} due to meeting conversion rates dropping to {conversion_kpi.current_value:.1f}%.",
                category=InsightCategory.BUSINESS_RISK,
                severity=InsightSeverity.HIGH if sales_health.status == HealthStatus.WARNING.value else InsightSeverity.CRITICAL,
                impact=InsightImpact.HIGH,
                confidence=0.85,
                evidence_graph=graph,
                related_kpis=[conversion_kpi.kpi_name],
                related_health_objects=[sales_health.health_name]
            )
            
        return None
