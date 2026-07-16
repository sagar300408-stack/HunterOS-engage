import abc
from typing import Optional
from uuid import UUID

from app.domain.recommendation.schemas import RecommendationGeneratorDefinition, RecommendationCalculationResult
from app.domain.insight.repository import InsightRepository
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository


class BaseRecommendationGenerator(abc.ABC):
    """
    Base class for Recommendation Generators.
    Generators consume Insights, Health, and KPI data to produce actionable recommendations.
    """

    @property
    @abc.abstractmethod
    def definition(self) -> RecommendationGeneratorDefinition:
        """
        Returns the metadata defining this recommendation generator.
        """
        pass

    @abc.abstractmethod
    async def analyze(self, insight_repo: InsightRepository, health_repo: HealthRepository, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> Optional[RecommendationCalculationResult]:
        """
        Calculates the recommendation and constructs the decision trace.
        Returns None if no actionable recommendation is warranted.
        """
        pass
