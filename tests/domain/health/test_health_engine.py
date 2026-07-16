import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.health.engine import OperationalHealthEngine
from app.domain.health.evaluators.standard_health import SalesHealthEvaluator, CustomerEngagementHealthEvaluator
from app.domain.health.models import HealthStatus, HealthTrend, HealthSeverity
from app.domain.kpi.models import KpiSnapshot, KpiStatus

# Important: these imports are necessary so SQLAlchemy mapping completes correctly in tests
from app.domain.kpi.models import KpiCategory, KpiDirection, KpiUnit, KpiStatus, KpiTrend
from app.domain.conversations import models as conv_models
from app.domain.customers import models as cust_models
from app.domain.scheduling import models as sched_models
from app.domain.followup import models as followup_models
from app.domain.intent import models as intent_models
from app.domain.memory import models as memory_models
from app.domain.health import models as health_models


@pytest.mark.asyncio
async def test_operational_health_engine_no_kpis():
    """
    Test when no KPIs are available, health status defaults to UNKNOWN.
    """
    mock_session = AsyncMock()
    
    mock_registry = MagicMock()
    mock_registry.get_all_evaluators.return_value = [CustomerEngagementHealthEvaluator()]
    
    engine = OperationalHealthEngine(mock_session)
    engine.kpi_repo.get_latest_snapshots = AsyncMock(return_value=[])
    engine.health_repo.get_health_trends = AsyncMock(return_value=[])
    engine.health_repo.save_snapshot = AsyncMock(side_effect=lambda x: x)
    
    workspace_id = uuid.uuid4()
    
    with patch("app.domain.health.engine.health_registry", mock_registry):
        snapshots = await engine.refresh_health(workspace_id, "workspace", workspace_id)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        
        assert snapshot.health_name == "customer_engagement_health"
        assert snapshot.status == HealthStatus.UNKNOWN.value
        assert snapshot.confidence == 0.0
        assert snapshot.trend == HealthTrend.UNKNOWN.value
        assert snapshot.severity == HealthSeverity.INFO.value


@pytest.mark.asyncio
async def test_operational_health_engine_with_kpis():
    """
    Test when KPIs are available, it evaluates and calculates trend properly.
    """
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    mock_registry = MagicMock()
    mock_registry.get_all_evaluators.return_value = [CustomerEngagementHealthEvaluator()]
    
    # Mock KPIs
    mock_kpi = KpiSnapshot(
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        kpi_name="reply_rate",
        current_value=45.0, # 45% -> GOOD (>=30)
        status=KpiStatus.HEALTHY.value
    )
    
    # Mock previous health snapshot (score 30.0) -> current 45.0 means UP
    mock_prev_health = health_models.HealthSnapshot(
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        health_name="customer_engagement_health",
        current_score=30.0,
        trend=HealthTrend.STABLE.value,
        status=HealthStatus.GOOD.value,
        severity=HealthSeverity.NORMAL.value,
        confidence=1.0
    )
    
    engine = OperationalHealthEngine(mock_session)
    engine.kpi_repo.get_latest_snapshots = AsyncMock(return_value=[mock_kpi])
    engine.health_repo.get_health_trends = AsyncMock(return_value=[mock_prev_health])
    engine.health_repo.save_snapshot = AsyncMock(side_effect=lambda x: x)
    
    with patch("app.domain.health.engine.health_registry", mock_registry):
        snapshots = await engine.refresh_health(workspace_id, "workspace", workspace_id)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        
        assert snapshot.health_name == "customer_engagement_health"
        assert snapshot.status == HealthStatus.GOOD.value
        assert snapshot.current_score == 45.0
        assert snapshot.trend == HealthTrend.UP.value
        assert snapshot.confidence == 1.0
        assert snapshot.supporting_evidence["reply_rate"] == 45.0
