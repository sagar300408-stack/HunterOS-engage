from typing import Optional
from uuid import UUID

from app.domain.recommendation.generators.base import BaseRecommendationGenerator
from app.domain.recommendation.schemas import (
    RecommendationGeneratorDefinition, RecommendationCalculationResult, 
    DecisionTrace, SuggestedAction,
    RecommendationCategory, ExpectedImpactCategory,
    RecommendationPriority, RecommendationRisk
)
from app.domain.insight.repository import InsightRepository
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository
from app.domain.insight.models import InsightCategory


class DecliningEngagementGenerator(BaseRecommendationGenerator):
    @property
    def definition(self) -> RecommendationGeneratorDefinition:
        return RecommendationGeneratorDefinition(
            name="DecliningEngagementGenerator",
            version="1.0",
            description="Recommends follow-up strategy adjustments when customer engagement declines."
        )

    async def analyze(self, insight_repo: InsightRepository, health_repo: HealthRepository, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> Optional[RecommendationCalculationResult]:
        insights = await insight_repo.get_latest_insights(target_type, target_id)
        
        # Look for a recent decline insight related to engagement
        decline_insight = next(
            (i for i in insights if i.category == InsightCategory.PERFORMANCE_DECLINE.value and 
             ("engagement" in i.title.lower() or "reply rate" in i.title.lower() or 
              ("customer_engagement_health" in i.related_health_objects))),
            None
        )
        
        if not decline_insight:
            return None
            
        decision_trace = DecisionTrace(
            insight_ids=[str(decline_insight.id)],
            health_ids=[h for h in decline_insight.related_health_objects],
            kpi_ids=[k for k in decline_insight.related_kpis],
            timeline_event_ids=[],
            explanation="Customer engagement is declining based on recent insights. Adjusting follow-up cadences may restore response rates."
        )
        
        action = SuggestedAction(
            action_type="UPDATE_FOLLOWUP_STRATEGY",
            description="Switch to the 'Gentle Nudge' cadence to reduce pressure and improve response rates.",
            target_entity="followup_cadence",
            parameters={"suggested_cadence_id": "gentle_nudge_cadence"}
        )
        
        return RecommendationCalculationResult(
            title="Adjust Follow-up Strategy",
            summary="Customer engagement has declined. We recommend adjusting your automated follow-ups to a less aggressive cadence.",
            category=RecommendationCategory.FOLLOWUP_STRATEGY,
            expected_impact=ExpectedImpactCategory.CUSTOMER_ENGAGEMENT,
            priority=RecommendationPriority.MEDIUM,
            risk_level=RecommendationRisk.LOW,
            recommendation_score=75.0,
            confidence=0.85,
            suggested_actions=[action],
            decision_trace=decision_trace
        )


class PipelineBottleneckGenerator(BaseRecommendationGenerator):
    @property
    def definition(self) -> RecommendationGeneratorDefinition:
        return RecommendationGeneratorDefinition(
            name="PipelineBottleneckGenerator",
            version="1.0",
            description="Recommends pipeline interventions when sales health is at risk."
        )

    async def analyze(self, insight_repo: InsightRepository, health_repo: HealthRepository, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> Optional[RecommendationCalculationResult]:
        insights = await insight_repo.get_latest_insights(target_type, target_id)
        
        risk_insight = next(
            (i for i in insights if i.category == InsightCategory.BUSINESS_RISK.value and 
             ("sales" in i.title.lower() or "pipeline" in i.title.lower() or 
              ("sales_health" in i.related_health_objects))),
            None
        )
        
        if not risk_insight:
            return None
            
        decision_trace = DecisionTrace(
            insight_ids=[str(risk_insight.id)],
            health_ids=[h for h in risk_insight.related_health_objects],
            kpi_ids=[k for k in risk_insight.related_kpis],
            timeline_event_ids=[],
            explanation="A significant risk to the sales pipeline was detected due to dropping conversion rates."
        )
        
        action1 = SuggestedAction(
            action_type="REVIEW_SALES_PIPELINE",
            description="Schedule a pipeline review meeting with the sales team to diagnose conversion drops.",
            target_entity="team_schedule",
            parameters={"meeting_type": "pipeline_review"}
        )
        
        action2 = SuggestedAction(
            action_type="OFFER_PROMOTION",
            description="Automatically trigger a re-engagement offer to stalled deals in the current pipeline.",
            target_entity="automation_workflow",
            parameters={"workflow_id": "reengagement_offer"}
        )
        
        return RecommendationCalculationResult(
            title="Intervene in Sales Pipeline",
            summary="Meeting conversion rates are threatening the sales pipeline. Immediate review and automated re-engagement are recommended.",
            category=RecommendationCategory.PIPELINE_MANAGEMENT,
            expected_impact=ExpectedImpactCategory.PIPELINE,
            priority=RecommendationPriority.HIGH,
            risk_level=RecommendationRisk.MEDIUM,
            recommendation_score=90.0,
            confidence=0.9,
            suggested_actions=[action1, action2],
            decision_trace=decision_trace
        )
