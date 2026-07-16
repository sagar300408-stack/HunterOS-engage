from uuid import UUID

from app.domain.health.evaluators.base import BaseHealthEvaluator
from app.domain.health.schemas import HealthDefinition, HealthCalculationResult, HealthStatus, HealthSeverity, HealthTrend
from app.domain.kpi.repository import KpiRepository


class SalesHealthEvaluator(BaseHealthEvaluator):
    @property
    def definition(self) -> HealthDefinition:
        return HealthDefinition(
            name="sales_health",
            description="Evaluates the overall health of the sales pipeline based on meeting conversions and pipeline KPIs.",
            required_kpis=["meeting_conversion_rate"]
        )

    async def evaluate(self, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> HealthCalculationResult:
        snapshots = await kpi_repo.get_latest_snapshots(target_type, target_id)
        
        # Find the meeting conversion rate KPI
        conversion_kpi = next((s for s in snapshots if s.kpi_name == "meeting_conversion_rate"), None)
        
        if not conversion_kpi:
            return HealthCalculationResult(
                current_score=0.0,
                status=HealthStatus.UNKNOWN,
                severity=HealthSeverity.INFO,
                trend=HealthTrend.UNKNOWN,
                confidence=0.0, # Low confidence because we lack required data
                supporting_evidence={"reason": "Missing required KPIs for Sales Health evaluation."}
            )

        # Baseline calculation from conversion rate (which is a percentage 0-100)
        # In a real scenario, this might blend multiple KPIs. For now, score = conversion_rate.
        score = conversion_kpi.current_value
        
        # Derive Status
        if score >= 40.0:
            status = HealthStatus.EXCELLENT
            severity = HealthSeverity.INFO
        elif score >= 20.0:
            status = HealthStatus.GOOD
            severity = HealthSeverity.NORMAL
        elif score >= 10.0:
            status = HealthStatus.WARNING
            severity = HealthSeverity.HIGH
        else:
            status = HealthStatus.CRITICAL
            severity = HealthSeverity.CRITICAL

        # Confidence: High if we found our required KPI
        confidence = 1.0

        supporting_evidence = {
            "meeting_conversion_rate": conversion_kpi.current_value,
            "meeting_conversion_status": conversion_kpi.status
        }
        
        return HealthCalculationResult(
            current_score=score,
            status=status,
            severity=severity,
            trend=HealthTrend.UNKNOWN, # Trend will be updated by engine based on historical scores
            confidence=confidence,
            supporting_evidence=supporting_evidence
        )


class CustomerEngagementHealthEvaluator(BaseHealthEvaluator):
    @property
    def definition(self) -> HealthDefinition:
        return HealthDefinition(
            name="customer_engagement_health",
            description="Evaluates how well customers are responding to communications.",
            required_kpis=["reply_rate"]
        )

    async def evaluate(self, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> HealthCalculationResult:
        snapshots = await kpi_repo.get_latest_snapshots(target_type, target_id)
        
        reply_kpi = next((s for s in snapshots if s.kpi_name == "reply_rate"), None)
        
        if not reply_kpi:
            return HealthCalculationResult(
                current_score=0.0,
                status=HealthStatus.UNKNOWN,
                severity=HealthSeverity.INFO,
                trend=HealthTrend.UNKNOWN,
                confidence=0.0,
                supporting_evidence={"reason": "Missing required KPIs for Customer Engagement Health evaluation."}
            )

        # Basic scoring
        score = reply_kpi.current_value

        # Derive Status
        if score >= 50.0:
            status = HealthStatus.EXCELLENT
            severity = HealthSeverity.INFO
        elif score >= 30.0:
            status = HealthStatus.GOOD
            severity = HealthSeverity.NORMAL
        elif score >= 15.0:
            status = HealthStatus.WARNING
            severity = HealthSeverity.HIGH
        else:
            status = HealthStatus.CRITICAL
            severity = HealthSeverity.CRITICAL
            
        supporting_evidence = {
            "reply_rate": reply_kpi.current_value,
            "reply_rate_status": reply_kpi.status
        }

        return HealthCalculationResult(
            current_score=score,
            status=status,
            severity=severity,
            trend=HealthTrend.UNKNOWN,
            confidence=1.0,
            supporting_evidence=supporting_evidence
        )
