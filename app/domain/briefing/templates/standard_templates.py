from typing import List, Dict, Any

from app.domain.briefing.templates.base import BaseBriefingTemplate
from app.domain.briefing.schemas import BriefingCalculationResult
from app.domain.insight.models import InsightSnapshot, InsightCategory, InsightSeverity
from app.domain.recommendation.models import RecommendationSnapshot, RecommendationPriority, RecommendationRisk
from app.domain.health.models import HealthSnapshot, HealthStatus
from app.domain.kpi.models import KpiSnapshot


class CEODailyBriefing(BaseBriefingTemplate):
    @property
    def template_name(self) -> str:
        return "ceo_daily"

    def compose(
        self,
        insights: List[InsightSnapshot],
        recommendations: List[RecommendationSnapshot],
        health_snapshots: List[HealthSnapshot],
        kpis: List[KpiSnapshot]
    ) -> BriefingCalculationResult:
        
        # 1. Filter High Priority Recommendations
        priority_recs = [r for r in recommendations if r.priority in [RecommendationPriority.HIGH.value, RecommendationPriority.URGENT.value]]
        
        # 2. Extract Critical Risks & Opportunities from Insights
        critical_risks = [i for i in insights if i.category == InsightCategory.BUSINESS_RISK.value and i.severity in [InsightSeverity.HIGH.value, InsightSeverity.CRITICAL.value]]
        opportunities = [i for i in insights if i.category == InsightCategory.BUSINESS_OPPORTUNITY.value]
        
        # 3. Highlight Key Insights
        key_insights = [i for i in insights if i.severity in [InsightSeverity.HIGH.value, InsightSeverity.CRITICAL.value] and i not in critical_risks]
        
        # 4. Summarize Health (Only flag non-good health to the CEO)
        health_summary = [{"name": h.health_name, "status": h.status, "trend": h.trend, "score": h.current_score} 
                          for h in health_snapshots if h.status not in [HealthStatus.EXCELLENT.value, HealthStatus.GOOD.value]]
        
        # 5. Extract KPI Highlights (Top 3 movers)
        sorted_kpis = sorted([k for k in kpis if k.percentage_change is not None], key=lambda x: abs(x.percentage_change), reverse=True)[:3]
        kpi_summary = [{"name": k.kpi_name, "value": k.current_value, "change": k.percentage_change} for k in sorted_kpis]
        
        # 6. Build References Array
        references = []
        for src in (priority_recs + critical_risks + opportunities + key_insights + health_snapshots + kpis):
            references.append(str(src.id))
            
        # 7. Confidence (Average of all used sources)
        sources_with_confidence = [x for x in (priority_recs + critical_risks + opportunities + key_insights) if hasattr(x, 'confidence')]
        avg_confidence = sum(x.confidence for x in sources_with_confidence) / len(sources_with_confidence) if sources_with_confidence else 1.0

        # 8. Generate Executive Summary text
        summary_text = "Overall operations are stable."
        if priority_recs or critical_risks:
            summary_text = f"Attention Required: {len(critical_risks)} critical risks detected and {len(priority_recs)} urgent recommendations await approval."
            
        return BriefingCalculationResult(
            executive_summary=summary_text,
            kpi_summary=kpi_summary,
            health_summary=health_summary,
            key_insights=[{"title": i.title, "summary": i.summary, "category": i.category} for i in key_insights],
            priority_recommendations=[{"title": r.title, "summary": r.summary, "actions": r.suggested_actions} for r in priority_recs],
            critical_risks=[{"title": i.title, "summary": i.summary} for i in critical_risks],
            business_opportunities=[{"title": i.title, "summary": i.summary} for i in opportunities],
            supporting_references=references,
            confidence=avg_confidence
        )


class SalesManagerBriefing(BaseBriefingTemplate):
    @property
    def template_name(self) -> str:
        return "sales_manager"

    def compose(
        self,
        insights: List[InsightSnapshot],
        recommendations: List[RecommendationSnapshot],
        health_snapshots: List[HealthSnapshot],
        kpis: List[KpiSnapshot]
    ) -> BriefingCalculationResult:
        
        sales_health = [h for h in health_snapshots if "sales" in h.health_name or "pipeline" in h.health_name]
        sales_recs = [r for r in recommendations if "sales" in r.category or "pipeline" in r.category]
        sales_insights = [i for i in insights if "sales" in i.category or "pipeline" in i.category]
        
        references = [str(x.id) for x in sales_health + sales_recs + sales_insights]
        
        summary_text = f"Sales Pipeline status is {sales_health[0].status if sales_health else 'UNKNOWN'}."
        
        return BriefingCalculationResult(
            executive_summary=summary_text,
            health_summary=[{"name": h.health_name, "status": h.status, "trend": h.trend, "score": h.current_score} for h in sales_health],
            key_insights=[{"title": i.title, "summary": i.summary} for i in sales_insights],
            priority_recommendations=[{"title": r.title, "summary": r.summary} for r in sales_recs],
            supporting_references=references,
            confidence=0.85
        )
