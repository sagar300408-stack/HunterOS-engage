import pytest
import uuid
import asyncio
from app.main import app as fastapi_app
from app.domain.onboarding.engines.workspace import WorkspaceEngine
from app.domain.onboarding.models import ProvisioningStatus
from sqlalchemy.ext.asyncio import AsyncSession
from tests.domain.events.conftest import pg_session, pg_session_factory, pg_engine

pytestmark = pytest.mark.asyncio

async def test_r7_workspace_provisioning(pg_session: AsyncSession):
    engine = WorkspaceEngine(pg_session)
    workspace_id = uuid.uuid4()
    
    # Run provisioning
    result = await engine.provision_workspace(
        workspace_id=workspace_id,
        owner_email=f"test_{workspace_id}@example.com",
        owner_name="Test User",
        password_hash="hashed_password"
    )
    
    assert result.status == ProvisioningStatus.COMPLETED
    assert result.current_step == "COMPLETE"
    
    # Test idempotency
    result2 = await engine.provision_workspace(
        workspace_id=workspace_id,
        owner_email=f"test_{workspace_id}@example.com",
        owner_name="Test User",
        password_hash="hashed_password"
    )
    assert result.id == result2.id
    assert result2.status == ProvisioningStatus.COMPLETED
