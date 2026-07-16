import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.repository import AnalyticsRepository
from app.domain.kpi.calculators.registry import kpi_registry
from app.domain.kpi.models import KpiDirection, KpiSnapshot, KpiStatus, KpiTrend
from app.domain.kpi.repository import KpiRepository
from app.domain.kpi.schemas import KpiDefinition


class KpiIntelligenceEngine:
    """
    Engine responsible for orchestrating the calculation of KPIs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.kpi_repo = KpiRepository(session)
        self.analytics_repo = AnalyticsRepository()

    def _determine_trend(self, current: float, previous: float, direction: str) -> str:
        if previous == 0 and current == 0:
            return KpiTrend.STABLE.value
        if previous == 0:
            return KpiTrend.UP.value if current > 0 else KpiTrend.DOWN.value

        change = (current - previous) / previous
        
        if abs(change) < 0.05:  # Less than 5% change is considered stable
            return KpiTrend.STABLE.value
            
        return KpiTrend.UP.value if current > previous else KpiTrend.DOWN.value

    def _determine_status(self, current: float, definition: KpiDefinition) -> str:
        if definition.critical_threshold is None and definition.warning_threshold is None:
            return KpiStatus.UNKNOWN.value

        is_higher_better = (definition.direction == KpiDirection.HIGHER_IS_BETTER)
        
        if is_higher_better:
            if definition.critical_threshold is not None and current <= definition.critical_threshold:
                return KpiStatus.CRITICAL.value
            if definition.warning_threshold is not None and current <= definition.warning_threshold:
                return KpiStatus.WARNING.value
            return KpiStatus.HEALTHY.value
        else:
            if definition.critical_threshold is not None and current >= definition.critical_threshold:
                return KpiStatus.CRITICAL.value
            if definition.warning_threshold is not None and current >= definition.warning_threshold:
                return KpiStatus.WARNING.value
            return KpiStatus.HEALTHY.value

    async def refresh_kpis(self, workspace_id: uuid.UUID, target_type: str, target_id: uuid.UUID) -> List[KpiSnapshot]:
        """
        Executes all registered KPI calculators for the given target and persists the snapshots.
        """
        calculators = kpi_registry.get_all_calculators()
        snapshots = []
        
        for calculator in calculators:
            definition = calculator.definition
            
            result = await calculator.calculate(
                self.session, 
                self.analytics_repo, 
                target_type, 
                target_id
            )
            
            trend = KpiTrend.STABLE.value
            if result.previous_value is not None:
                trend = self._determine_trend(result.current_value, result.previous_value, definition.direction)
                
            status = self._determine_status(result.current_value, definition)
            
            snapshot = KpiSnapshot(
                workspace_id=workspace_id,
                target_type=target_type,
                target_id=target_id,
                kpi_name=definition.name,
                category=definition.category.value,
                description=definition.description,
                unit=definition.unit.value,
                direction=definition.direction.value,
                current_value=result.current_value,
                previous_value=result.previous_value,
                percentage_change=result.percentage_change,
                trend=trend,
                status=status,
                target=definition.target,
                warning_threshold=definition.warning_threshold,
                critical_threshold=definition.critical_threshold,
                confidence=result.confidence,
                data_source=definition.data_source,
                refresh_strategy=definition.refresh_strategy
            )
            
            saved_snapshot = await self.kpi_repo.save_snapshot(snapshot)
            snapshots.append(saved_snapshot)
            
        return snapshots
