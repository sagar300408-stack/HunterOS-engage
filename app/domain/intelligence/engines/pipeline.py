import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.repository import IntelligenceRepository
from app.domain.intelligence.models import OperationalHealthSnapshot
from app.domain.intelligence.engines.leakage import OpportunityLeakageEngine
from app.domain.intelligence.engines.root_cause import RootCauseEngine
from app.domain.intelligence.engines.prediction import PredictionEngine
from app.domain.intelligence.engines.insight import InsightEngine

# We reuse the detectors from the friction domain
from app.domain.friction.scoring import FrictionScoreEngine
from app.domain.friction.detectors.lead_response import LeadResponseMonitor
from app.domain.friction.detectors.approval_delay import ApprovalDelayDetector
from app.domain.friction.detectors.sla_monitor import SLAMonitoringEngine
from app.domain.friction.detectors.workflow_bottleneck import WorkflowBottleneckDetector
from app.domain.friction.recommendations import FrictionRecommendationEngine
from app.domain.friction.models import SLAPolicy

logger = logging.getLogger(__name__)

class OperationalIntelligencePipeline:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IntelligenceRepository(session)
        
        self.leakage_engine = OpportunityLeakageEngine(session)
        self.root_cause_engine = RootCauseEngine(session)
        self.prediction_engine = PredictionEngine(session)
        self.insight_engine = InsightEngine(session)
        
        self.friction_scorer = FrictionScoreEngine(session)
        self.friction_recommender = FrictionRecommendationEngine(session)

    async def run(self, workspace_id: uuid.UUID) -> OperationalHealthSnapshot:
        """
        Executes the entire intelligence pipeline for a workspace.
        """
        # 1. Debounce Check
        should_run = await self.repo.check_debounce_and_lock(workspace_id)
        if not should_run:
            logger.debug(f"Pipeline debounced for workspace {workspace_id}")
            return await self.repo.get_latest_health_snapshot(workspace_id)

        logger.info(f"Running Operational Intelligence Pipeline for {workspace_id}")

        # 2. Leakage Engine (quantifies lost ₹)
        await self.leakage_engine.scan_leakages(workspace_id)
        
        # 3. Friction Detectors (Populate FrictionEvents)
        await LeadResponseMonitor(self.session).scan_idle_leads(workspace_id)
        await ApprovalDelayDetector(self.session).scan_pending_approvals(workspace_id)
        
        # We need SLA policies to run the SLA monitor
        from sqlalchemy import select
        policies = (await self.session.execute(
            select(SLAPolicy).where(SLAPolicy.workspace_id == workspace_id, SLAPolicy.is_active == True)
        )).scalars().all()
        await SLAMonitoringEngine(self.session).scan_sla_violations(workspace_id, policies)
        
        await WorkflowBottleneckDetector(self.session).scan_stalled_deals(workspace_id)

        # 4. Score Friction
        friction_snapshot = await self.friction_scorer.calculate_score(workspace_id)
        
        # 5. Build Health Snapshot
        previous_health = await self.repo.get_latest_health_snapshot(workspace_id)
        
        # Calculate Leakage Score
        active_leakages = await self.repo.get_active_leakages(workspace_id)
        total_leakage = sum(l.revenue_at_risk for l in active_leakages)
        # Cap leakage score at 100 based on a 1M INR threshold for severity
        leakage_score = min(100.0, (total_leakage / 1000000.0) * 100.0)
        
        # Determine risk score (we will adjust this after predictions, but give it a base)
        base_risk = friction_snapshot.score * 0.5
        
        # Calculate overall Health Index (inverse of friction, risk, leakage)
        # Weight: 40% Friction, 30% Leakage, 30% Risk
        health_index = max(0.0, 100.0 - (friction_snapshot.score * 0.4 + leakage_score * 0.3 + base_risk * 0.3))

        new_health = OperationalHealthSnapshot(
            workspace_id=workspace_id,
            health_index=round(health_index, 2),
            friction_score=friction_snapshot.score,
            risk_score=round(base_risk, 2),
            leakage_score=round(leakage_score, 2),
            trend=friction_snapshot.trend,
            calculated_at=datetime.now(timezone.utc)
        )

        if previous_health:
            new_health.health_delta = round(new_health.health_index - previous_health.health_index, 2)
            new_health.friction_delta = friction_snapshot.score_delta
            new_health.risk_delta = round(new_health.risk_score - previous_health.risk_score, 2)
            new_health.leakage_delta = round(new_health.leakage_score - previous_health.leakage_score, 2)

        self.session.add(new_health)

        # 6. Root Cause Engine
        await self.root_cause_engine.analyze(workspace_id)

        # 7. Prediction Engine
        predictions = await self.prediction_engine.run_predictions(workspace_id, new_health)
        
        # Adjust risk score based on predictions
        if predictions:
            max_confidence = max(p.confidence_score for p in predictions)
            new_health.risk_score = min(100.0, new_health.risk_score + (max_confidence * 20.0))
            new_health.health_index = max(0.0, 100.0 - (new_health.friction_score * 0.4 + new_health.leakage_score * 0.3 + new_health.risk_score * 0.3))

        # 8. Insight Engine
        await self.insight_engine.generate_insight(workspace_id, new_health)

        # 9. Recommendations (Action generation based on Friction)
        await self.friction_recommender.generate_recommendations(workspace_id)

        # Flush all generated entities
        await self.session.flush()

        return new_health
