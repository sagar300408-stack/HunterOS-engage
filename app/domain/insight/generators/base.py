import abc
from typing import Optional
from uuid import UUID

from app.domain.insight.schemas import InsightGeneratorDefinition, InsightCalculationResult
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository
# Currently TimelineRepository is not defined in the scope of this file so we just assume it is passed.
# In a real app we would import it.


class BaseInsightGenerator(abc.ABC):
    """
    Base class for Insight Generators.
    Generators consume KPI, Health, and Timeline data to discover and explain operational insights.
    """

    @property
    @abc.abstractmethod
    def definition(self) -> InsightGeneratorDefinition:
        """
        Returns the metadata defining this insight generator.
        """
        pass

    @abc.abstractmethod
    async def analyze(self, kpi_repo: KpiRepository, health_repo: HealthRepository, target_type: str, target_id: UUID) -> Optional[InsightCalculationResult]:
        """
        Calculates the insight and constructs the evidence graph.
        Returns None if no actionable insight was found for this domain.
        """
        pass
