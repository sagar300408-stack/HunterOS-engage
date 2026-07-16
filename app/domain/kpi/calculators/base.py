from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.repository import AnalyticsRepository
from app.domain.kpi.schemas import KpiCalculationResult, KpiDefinition


class BaseKpiCalculator(ABC):
    """
    Abstract base class for all KPI Calculators.
    """
    
    @property
    @abstractmethod
    def definition(self) -> KpiDefinition:
        """Return the rich metadata definition of this KPI."""
        pass

    @abstractmethod
    async def calculate(
        self, 
        session: AsyncSession, 
        analytics_repo: AnalyticsRepository, 
        target_type: str, 
        target_id: UUID
    ) -> KpiCalculationResult:
        """
        Calculate the KPI using data from the AnalyticsRepository.
        
        Must return a KpiCalculationResult containing the current value, 
        and optionally the previous value and percentage change if applicable.
        """
        pass
