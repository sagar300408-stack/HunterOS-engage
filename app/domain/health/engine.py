import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.health.repository import HealthRepository
from app.domain.health.models import HealthSnapshot, HealthTrend, HealthStatus
from app.domain.health.evaluators.registry import health_registry
from app.domain.kpi.repository import KpiRepository


logger = logging.getLogger(__name__)


class OperationalHealthEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.health_repo = HealthRepository(session)
        self.kpi_repo = KpiRepository(session)
        
    async def refresh_health(self, workspace_id: UUID, target_type: str, target_id: UUID) -> List[HealthSnapshot]:
        """
        Runs all registered health evaluators for the given target, computing
        the new health snapshots based on the latest KPIs.
        """
        snapshots = []
        evaluators = health_registry.get_all_evaluators()
        
        for evaluator in evaluators:
            try:
                # 1. Fetch previous health snapshot to compute trend
                previous_snapshots = await self.health_repo.get_health_trends(
                    target_type, target_id, evaluator.definition.name, limit=1
                )
                previous_snapshot = previous_snapshots[0] if previous_snapshots else None
                
                # 2. Execute Evaluator (which fetches required KPIs)
                result = await evaluator.evaluate(self.kpi_repo, target_type, target_id)
                
                # 3. Determine Trend
                trend = self._determine_trend(result.current_score, previous_snapshot)
                
                # 4. Construct Snapshot
                snapshot = HealthSnapshot(
                    workspace_id=workspace_id,
                    target_type=target_type,
                    target_id=target_id,
                    health_name=evaluator.definition.name,
                    description=evaluator.definition.description,
                    current_score=result.current_score,
                    previous_score=previous_snapshot.current_score if previous_snapshot else None,
                    trend=trend.value,
                    status=result.status.value,
                    severity=result.severity.value,
                    confidence=result.confidence,
                    evaluation_version=evaluator.definition.version,
                    related_kpis=evaluator.definition.required_kpis,
                    supporting_evidence=result.supporting_evidence,
                )
                
                # 5. Save Snapshot
                saved_snapshot = await self.health_repo.save_snapshot(snapshot)
                snapshots.append(saved_snapshot)
            except Exception as e:
                logger.error(f"Failed to evaluate health domain {evaluator.definition.name}: {e}")
        from app.domain.insight.engine import InsightEngine
        insight_engine = InsightEngine(self.session)
        await insight_engine.generate_insights(workspace_id, target_type, target_id)
                
        return snapshots

    def _determine_trend(self, current_score: float, previous_snapshot: Optional[HealthSnapshot]) -> HealthTrend:
        if not previous_snapshot:
            return HealthTrend.UNKNOWN
            
        prev_score = previous_snapshot.current_score
        
        # Simple thresholding for trend
        diff = current_score - prev_score
        if diff > 1.0:
            return HealthTrend.UP
        elif diff < -1.0:
            return HealthTrend.DOWN
        else:
            return HealthTrend.STABLE
