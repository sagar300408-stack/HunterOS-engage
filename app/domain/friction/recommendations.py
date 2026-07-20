"""
FrictionRecommendationEngine
─────────────────────────────
Maps detected FrictionEvents to actionable RecommendationSnapshots.
Reuses the existing RecommendationSnapshot model to keep data unified.

Each friction type has one or more recommendation templates with:
  - Title + Summary
  - Suggested actions (step-by-step)
  - Expected impact (% friction reduction estimate)
  - Priority and risk level
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import FrictionEvent, FrictionType
from app.domain.recommendation.models import (
    RecommendationSnapshot,
    RecommendationCategory,
    ExpectedImpactCategory,
    RecommendationPriority,
    RecommendationRisk,
    RecommendationLifecycle,
)

logger = logging.getLogger(__name__)


# ── Recommendation Templates ──────────────────────────────────────────────────

_TEMPLATES: Dict[str, dict] = {
    FrictionType.LEAD_RESPONSE_DELAY.value: {
        "title": "Reduce Lead Response Delays",
        "summary": (
            "Lead response times are exceeding acceptable thresholds, causing significant "
            "conversion rate drops. Studies show a 10× decrease in contact rate after 5 minutes."
        ),
        "actions": [
            {"step": 1, "action": "Assign additional SDR coverage between 9 AM – 12 PM peak hours"},
            {"step": 2, "action": "Enable automated WhatsApp greeting for all new leads within 2 minutes"},
            {"step": 3, "action": "Set up escalation alert if no contact within 30 minutes"},
        ],
        "expected_impact": "Reduce friction contribution by 14% and improve conversion rate by 22%.",
        "category": RecommendationCategory.SALES_OPTIMIZATION.value,
        "impact_category": ExpectedImpactCategory.REVENUE.value,
        "priority": RecommendationPriority.HIGH.value,
        "risk": RecommendationRisk.LOW.value,
        "score": 85.0,
    },
    FrictionType.MISSED_FOLLOWUP.value: {
        "title": "Fix Missed Follow-up Execution",
        "summary": (
            "Scheduled follow-ups are not being executed on time. This creates customer "
            "engagement gaps and signals systemic follow-up engine issues."
        ),
        "actions": [
            {"step": 1, "action": "Investigate follow-up engine health and execution logs"},
            {"step": 2, "action": "Implement dead-letter queue for failed follow-up messages"},
            {"step": 3, "action": "Enable supervisor alerts for follow-ups overdue by >30 minutes"},
        ],
        "expected_impact": "Eliminate follow-up gaps and reduce friction by 11%.",
        "category": RecommendationCategory.FOLLOWUP_STRATEGY.value,
        "impact_category": ExpectedImpactCategory.CUSTOMER_ENGAGEMENT.value,
        "priority": RecommendationPriority.HIGH.value,
        "risk": RecommendationRisk.LOW.value,
        "score": 78.0,
    },
    FrictionType.SLA_VIOLATION.value: {
        "title": "Restore SLA Compliance",
        "summary": (
            "Multiple SLA violations detected. This directly impacts customer satisfaction "
            "scores and signals operational capacity issues."
        ),
        "actions": [
            {"step": 1, "action": "Audit current team capacity against lead volume"},
            {"step": 2, "action": "Enable automated WhatsApp outreach for new leads as SLA safety net"},
            {"step": 3, "action": "Adjust SLA thresholds to reflect realistic capacity if needed"},
        ],
        "expected_impact": "Restore SLA compliance to 95%+ and reduce friction by 16%.",
        "category": RecommendationCategory.OPERATIONAL_EFFICIENCY.value,
        "impact_category": ExpectedImpactCategory.CUSTOMER_ENGAGEMENT.value,
        "priority": RecommendationPriority.URGENT.value,
        "risk": RecommendationRisk.MEDIUM.value,
        "score": 90.0,
    },
    FrictionType.APPROVAL_DELAY.value: {
        "title": "Eliminate Approval Bottlenecks",
        "summary": (
            "Approval requests are creating downstream operational blockages. "
            "Pending approvals prevent deals from progressing and delay customer commitments."
        ),
        "actions": [
            {"step": 1, "action": "Delegate approvals below ₹50,000 to Sales Managers automatically"},
            {"step": 2, "action": "Set up escalation: auto-escalate after 4 hours with no decision"},
            {"step": 3, "action": "Introduce parallel approval for non-conflicting requests"},
        ],
        "expected_impact": "Reduce approval cycle time by 67% and save ~18 hours/week.",
        "category": RecommendationCategory.PROCESS_IMPROVEMENT.value,
        "impact_category": ExpectedImpactCategory.EFFICIENCY.value,
        "priority": RecommendationPriority.URGENT.value,
        "risk": RecommendationRisk.MEDIUM.value,
        "score": 92.0,
    },
    FrictionType.WORKFLOW_STALL.value: {
        "title": "Unblock Stalled Pipeline Stages",
        "summary": (
            "One or more pipeline stages have average lead dwell times significantly exceeding "
            "expected baselines, signaling bottlenecks that reduce deal velocity."
        ),
        "actions": [
            {"step": 1, "action": "Review leads stalled in bottleneck stage and assign ownership"},
            {"step": 2, "action": "Auto-escalate leads with no stage movement after 1.5× baseline"},
            {"step": 3, "action": "Introduce stage-specific SLAs with automated nudges"},
        ],
        "expected_impact": "Reduce average sales cycle by 22% and improve pipeline velocity.",
        "category": RecommendationCategory.PIPELINE_MANAGEMENT.value,
        "impact_category": ExpectedImpactCategory.PIPELINE.value,
        "priority": RecommendationPriority.HIGH.value,
        "risk": RecommendationRisk.LOW.value,
        "score": 80.0,
    },
    FrictionType.OPPORTUNITY_LEAKAGE.value: {
        "title": "Prevent Opportunity Leakage",
        "summary": (
            "Qualified leads are dropping out of the pipeline without conversion. "
            "Revenue potential is being lost due to insufficient engagement."
        ),
        "actions": [
            {"step": 1, "action": "Identify top 10 high-score leads with no recent activity"},
            {"step": 2, "action": "Trigger personalized re-engagement campaign immediately"},
            {"step": 3, "action": "Implement automated win-back sequence for leads inactive >7 days"},
        ],
        "expected_impact": "Recover 15–20% of at-risk opportunities.",
        "category": RecommendationCategory.BUSINESS_OPPORTUNITY.value,
        "impact_category": ExpectedImpactCategory.REVENUE.value,
        "priority": RecommendationPriority.HIGH.value,
        "risk": RecommendationRisk.LOW.value,
        "score": 82.0,
    },
    FrictionType.CUSTOMER_INACTIVITY.value: {
        "title": "Re-engage Inactive Customers",
        "summary": (
            "Multiple customers show extended periods of inactivity, "
            "increasing churn risk and reducing lifetime value."
        ),
        "actions": [
            {"step": 1, "action": "Segment inactive customers by last interaction date"},
            {"step": 2, "action": "Launch automated re-engagement WhatsApp sequence"},
            {"step": 3, "action": "Flag high-value inactive customers for personal SDR outreach"},
        ],
        "expected_impact": "Re-engage 25–35% of inactive customers, reducing churn risk.",
        "category": RecommendationCategory.CUSTOMER_ENGAGEMENT.value,
        "impact_category": ExpectedImpactCategory.CUSTOMER_ENGAGEMENT.value,
        "priority": RecommendationPriority.MEDIUM.value,
        "risk": RecommendationRisk.LOW.value,
        "score": 65.0,
    },
}


class FrictionRecommendationEngine:
    """Converts FrictionEvents into actionable RecommendationSnapshots."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_recommendations(
        self, workspace_id: UUID, friction_events: List[FrictionEvent]
    ) -> List[RecommendationSnapshot]:
        """
        For each unique friction type in the event list, generate one
        RecommendationSnapshot using the template registry.
        """
        recommendations = []
        seen_types = set()

        for event in friction_events:
            ftype = event.friction_type
            if ftype in seen_types:
                continue  # One recommendation per friction type per scan
            seen_types.add(ftype)

            template = _TEMPLATES.get(ftype)
            if not template:
                continue

            rec = RecommendationSnapshot(
                workspace_id=workspace_id,
                target_type="workspace",
                target_id=workspace_id,
                title=template["title"],
                summary=f"{template['summary']}\n\nExpected Impact: {template['expected_impact']}",
                category=template["category"],
                expected_impact=template["impact_category"],
                priority=template["priority"],
                risk_level=template["risk"],
                lifecycle_status=RecommendationLifecycle.ACTIVE.value,
                recommendation_score=template["score"],
                confidence=min(0.95, 0.5 + (event.score_contribution / 40.0)),
                suggested_actions=template["actions"],
                decision_trace={
                    "friction_type": ftype,
                    "friction_event_id": str(event.id) if event.id else None,
                    "score_contribution": event.score_contribution,
                    "severity": event.severity,
                },
                generator_name="FrictionRecommendationEngine",
                generator_version="1.0",
                trigger_source=f"friction.{ftype.lower()}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            self.session.add(rec)
            recommendations.append(rec)

        if recommendations:
            await self.session.flush()

        return recommendations
