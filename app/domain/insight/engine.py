import logging
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.insight.repository import InsightRepository
from app.domain.insight.models import InsightSnapshot, InsightLifecycle
from app.domain.insight.generators.registry import insight_registry
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository


logger = logging.getLogger(__name__)


class InsightEngine:
    """
    Engine responsible for executing Insight Generators and persisting explanations.
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.insight_repo = InsightRepository(session)
        self.health_repo = HealthRepository(session)
        self.kpi_repo = KpiRepository(session)
        
    async def generate_insights(self, workspace_id: UUID, target_type: str, target_id: UUID) -> List[InsightSnapshot]:
        snapshots = []
        generators = insight_registry.get_all_generators()
        
        for generator in generators:
            try:
                # 1. Execute Generator
                result = await generator.analyze(self.kpi_repo, self.health_repo, target_type, target_id)
                
                # 2. Skip if no insight found
                if not result:
                    continue
                
                # 3. Serialize Evidence Graph properly to dict
                evidence_dict = result.evidence_graph.model_dump()
                
                # 4. Construct Snapshot
                snapshot = InsightSnapshot(
                    workspace_id=workspace_id,
                    target_type=target_type,
                    target_id=target_id,
                    title=result.title,
                    summary=result.summary,
                    category=result.category.value,
                    severity=result.severity.value,
                    impact=result.impact.value,
                    lifecycle_status=InsightLifecycle.ACTIVE.value,
                    confidence=result.confidence,
                    evidence_graph=evidence_dict,
                    graph_version=result.evidence_graph.version,
                    related_kpis=result.related_kpis,
                    related_health_objects=result.related_health_objects,
                    related_timeline_events=result.related_timeline_events,
                    generator_name=generator.definition.name,
                    generator_version=generator.definition.version,
                    trigger_source="health_refresh"
                )
                
                # 5. Save Snapshot (this handles superseding duplicates automatically)
                saved_snapshot = await self.insight_repo.save_insight(snapshot)
                snapshots.append(saved_snapshot)
                
            except Exception as e:
                logger.error(f"Failed to generate insight using {generator.definition.name}: {e}")
                
        return snapshots
