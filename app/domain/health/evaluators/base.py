import abc
from uuid import UUID

from app.domain.health.schemas import HealthDefinition, HealthCalculationResult
from app.domain.kpi.repository import KpiRepository


class BaseHealthEvaluator(abc.ABC):
    """
    Base class for Operational Health evaluators.
    Evaluators consume KPI snapshots to determine a domain's health.
    """

    @property
    @abc.abstractmethod
    def definition(self) -> HealthDefinition:
        """
        Returns the metadata defining this health evaluation domain,
        including required KPIs.
        """
        pass

    @abc.abstractmethod
    async def evaluate(self, kpi_repo: KpiRepository, target_type: str, target_id: UUID) -> HealthCalculationResult:
        """
        Calculates the health score, status, and supporting evidence based purely on KPIs.
        """
        pass
