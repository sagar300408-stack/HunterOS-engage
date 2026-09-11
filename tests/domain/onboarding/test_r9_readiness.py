import pytest
import uuid
from app.main import app as fastapi_app
from app.domain.onboarding.engines.readiness import ReadinessEngine
from app.domain.onboarding.engines.golive import GoliveEngine
from app.domain.onboarding.engines.workspace import WorkspaceEngine
from app.domain.onboarding.models import GoLiveStatus
from sqlalchemy.ext.asyncio import AsyncSession
from tests.domain.events.conftest import pg_session, pg_session_factory, pg_engine
from app.domain.context.models import OrganizationNode
from app.domain.integration.models import IntegrationConnection

pytestmark = pytest.mark.asyncio

async def test_r9_readiness_and_golive(pg_session: AsyncSession):
    workspace_engine = WorkspaceEngine(pg_session)
    golive_engine = GoliveEngine(pg_session)
    workspace_id = uuid.uuid4()
    
    # Needs provisioning first
    await workspace_engine.provision_workspace(
        workspace_id=workspace_id,
        owner_email=f"test_{workspace_id}@example.com",
        owner_name="Test User",
        password_hash="hashed"
    )
    
    # Assess - should be NOT_READY
    assessment = await golive_engine.execute(workspace_id)
    assert assessment.status == GoLiveStatus.NOT_READY
    
    # Add requirements
    node = OrganizationNode(
        workspace_id=workspace_id,
        node_type="Company",
        name="Test Corp",
        source_system="MANUAL"
    )
    pg_session.add(node)
    conn = IntegrationConnection(
        workspace_id=workspace_id,
        connector_id="mock_email_v1",
        connector_type="email",
        provider="mock",
        name="Email Setup",
        status="connected"
    )
    pg_session.add(conn)
    await pg_session.commit()
    
    # Assess again - should be READY
    assessment2 = await golive_engine.execute(workspace_id)
    assert assessment2.status == GoLiveStatus.READY
