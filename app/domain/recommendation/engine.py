import logging
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recommendation.repository import RecommendationRepository
from app.domain.recommendation.models import RecommendationSnapshot, RecommendationLifecycle
from app.domain.recommendation.generators.registry import recommendation_registry
from app.domain.insight.repository import InsightRepository
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository


logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Engine responsible for executing Recommendation Generators and proposing actionable decisions.
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.recommendation_repo = RecommendationRepository(session)
        self.insight_repo = InsightRepository(session)
        self.health_repo = HealthRepository(session)
        self.kpi_repo = KpiRepository(session)
        
    async def generate_recommendations(self, workspace_id: UUID, target_type: str, target_id: UUID) -> List[RecommendationSnapshot]:
        snapshots = []
        generators = recommendation_registry.get_all_generators()
        
        for generator in generators:
            try:
                # 1. Execute Generator
                result = await generator.analyze(self.insight_repo, self.health_repo, self.kpi_repo, target_type, target_id)
                
                # 2. Skip if no recommendation is warranted
                if not result:
                    continue
                
                # 3. Serialize Decision Trace and Suggested Actions
                trace_dict = result.decision_trace.model_dump()
                actions_list = [a.model_dump() for a in result.suggested_actions]
                
                # 4. Construct Snapshot
                snapshot = RecommendationSnapshot(
                    workspace_id=workspace_id,
                    target_type=target_type,
                    target_id=target_id,
                    title=result.title,
                    summary=result.summary,
                    category=result.category.value,
                    expected_impact=result.expected_impact.value,
                    priority=result.priority.value,
                    risk_level=result.risk_level.value,
                    lifecycle_status=RecommendationLifecycle.ACTIVE.value,
                    expires_at=result.expires_at,
                    recommendation_score=result.recommendation_score,
                    confidence=result.confidence,
                    suggested_actions=actions_list,
                    decision_trace=trace_dict,
                    generator_name=generator.definition.name,
                    generator_version=generator.definition.version,
                    trigger_source="insight_generation"
                )
                
                # 5. Save Snapshot (superseding duplicates)
                saved_snapshot = await self.recommendation_repo.save_recommendation(snapshot)
                snapshots.append(saved_snapshot)
                
            except Exception as e:
                logger.error(f"Failed to generate recommendation using {generator.definition.name}: {e}")
                
        return snapshots
