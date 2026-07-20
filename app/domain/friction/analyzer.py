"""
BusinessFrictionAnalyzer
─────────────────────────
Central orchestrator of the Business Friction Engine.

Runs a complete friction scan across all detectors,
persists FrictionEvents, triggers score recalculation,
and generates recommendations.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.detectors.lead_response     import LeadResponseMonitor
from app.domain.friction.detectors.sla_monitor        import SLAMonitoringEngine
from app.domain.friction.detectors.approval_delay     import ApprovalDelayDetector
from app.domain.friction.detectors.workflow_bottleneck import WorkflowBottleneckDetector
from app.domain.friction.models import FrictionEvent
from app.domain.friction.repository import FrictionRepository
from app.domain.friction.scoring import FrictionScoreEngine
from app.domain.friction.recommendations import FrictionRecommendationEngine

logger = logging.getLogger(__name__)


class BusinessFrictionAnalyzer:
    """
    Orchestrates all detectors, persists results, and coordinates
    scoring and recommendation generation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo    = FrictionRepository(session)

    async def run_full_scan(self, workspace_id: UUID) -> dict:
        """
        Execute a complete friction scan for the workspace.
        Returns a summary of what was detected and the new BFS.
        """
        logger.info("friction_scan_start", extra={"workspace_id": str(workspace_id)})

        all_events: List[FrictionEvent] = []

        # ── 1. Lead Response Monitor ──────────────────────────────────────────
        try:
            monitor = LeadResponseMonitor(self.session)
            lead_events = await monitor.scan_idle_leads(workspace_id)
            all_events.extend(lead_events)
        except Exception as e:
            logger.warning("lead_monitor_failed", extra={"error": str(e)})

        # ── 2. SLA Monitoring Engine ──────────────────────────────────────────
        try:
            policies = await self.repo.get_sla_policies(workspace_id)
            if policies:
                sla_engine = SLAMonitoringEngine(self.session)
                sla_events = await sla_engine.scan_sla_violations(workspace_id, policies)
                all_events.extend(sla_events)
        except Exception as e:
            logger.warning("sla_monitor_failed", extra={"error": str(e)})

        # ── 3. Approval Delay Detector ────────────────────────────────────────
        try:
            approval_detector = ApprovalDelayDetector(self.session)
            approval_events = await approval_detector.scan_delayed_approvals(workspace_id)
            all_events.extend(approval_events)
        except Exception as e:
            logger.warning("approval_detector_failed", extra={"error": str(e)})

        # ── 4. Workflow Bottleneck Detector ───────────────────────────────────
        try:
            bottleneck_detector = WorkflowBottleneckDetector(self.session, self.repo)
            wf_events = await bottleneck_detector.scan_workflow_bottlenecks(workspace_id)
            all_events.extend(wf_events)
        except Exception as e:
            logger.warning("bottleneck_detector_failed", extra={"error": str(e)})

        # ── 5. Persist all detected friction events ───────────────────────────
        saved = []
        for event in all_events:
            try:
                saved.append(await self.repo.save_friction_event(event))
            except Exception as e:
                logger.error("friction_event_save_failed", extra={"error": str(e)})

        # ── 6. Compute new Business Friction Score ────────────────────────────
        score_engine = FrictionScoreEngine(self.repo)
        snapshot = await score_engine.compute_score(workspace_id)
        await self.repo.save_score_snapshot(snapshot)

        # ── 7. Generate recommendations from open friction ────────────────────
        try:
            rec_engine = FrictionRecommendationEngine(self.session)
            await rec_engine.generate_recommendations(workspace_id, saved)
        except Exception as e:
            logger.warning("recommendation_gen_failed", extra={"error": str(e)})

        logger.info(
            "friction_scan_complete",
            extra={
                "workspace_id": str(workspace_id),
                "events_detected": len(saved),
                "new_score": snapshot.score,
            }
        )

        return {
            "friction_events_detected": len(saved),
            "new_score": snapshot.score,
            "previous_score": snapshot.previous_score,
        }
