import uuid
from datetime import datetime, timezone
import pytest

from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.kpi.engine import KpiIntelligenceEngine
from app.domain.kpi.calculators.base import BaseKpiCalculator
from app.domain.kpi.schemas import KpiDefinition, KpiCalculationResult
from app.domain.kpi.models import KpiCategory, KpiDirection, KpiUnit, KpiStatus, KpiTrend
from app.domain.conversations import models as conv_models
from app.domain.customers import models as cust_models
from app.domain.scheduling import models as sched_models
from app.domain.followup import models as followup_models
from app.domain.intent import models as intent_models
from app.domain.memory import models as memory_models


class MockMeetingConversionRateCalculator(BaseKpiCalculator):
    @property
    def definition(self) -> KpiDefinition:
        return KpiDefinition(
            name="meeting_conversion_rate",
            category=KpiCategory.SALES,
            description="Test KPI",
            unit=KpiUnit.PERCENTAGE,
            direction=KpiDirection.HIGHER_IS_BETTER,
            target=25.0,
            warning_threshold=15.0,
            critical_threshold=10.0,
            data_source="analytics_projection",
            refresh_strategy="daily"
        )

    async def calculate(self, session, analytics_repo, target_type, target_id) -> KpiCalculationResult:
        # Mock calculation: 
        # Current = 20.0, Previous = 10.0 => +100%
        return KpiCalculationResult(
            current_value=20.0,
            previous_value=10.0,
            percentage_change=100.0,
            confidence=0.9
        )


@pytest.mark.asyncio
async def test_kpi_intelligence_engine():
    # Setup mock registry with our single calculator
    mock_registry = MagicMock()
    mock_registry.get_all_calculators.return_value = [MockMeetingConversionRateCalculator()]

    mock_session = AsyncMock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    with patch("app.domain.kpi.engine.kpi_registry", mock_registry):
        with patch("app.domain.kpi.engine.ImpactRepository") as MockImpactRepo:
            mock_impact_repo = MockImpactRepo.return_value
            mock_impact_repo.get_business_targets = AsyncMock(return_value=[])
            
            engine = KpiIntelligenceEngine(mock_session)
    
            # Mock the repo save so we can inspect the snapshot being saved
            engine.kpi_repo.save_snapshot = AsyncMock(side_effect=lambda x: x)
        
        workspace_id = uuid.uuid4()
        
        snapshots = await engine.refresh_kpis(workspace_id, "workspace", workspace_id)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        
        # Verify the calculation data
        assert snapshot.kpi_name == "meeting_conversion_rate"
        assert snapshot.current_value == 20.0
        assert snapshot.previous_value == 10.0
        assert snapshot.percentage_change == 100.0
        assert snapshot.confidence == 0.9
        
        # Verify trend and status logic
        assert snapshot.trend == KpiTrend.UP.value
        # 20.0 is > 15.0 (warning) and > 10.0 (critical), and target is higher_is_better. So it should be HEALTHY
        assert snapshot.status == KpiStatus.HEALTHY.value
