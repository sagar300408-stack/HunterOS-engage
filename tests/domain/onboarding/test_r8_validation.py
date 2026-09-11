import pytest
import uuid
from app.main import app as fastapi_app
from app.domain.onboarding.engines.validation import ValidationEngine
from app.domain.onboarding.engines.workspace import WorkspaceEngine
from sqlalchemy.ext.asyncio import AsyncSession
from tests.domain.events.conftest import pg_session, pg_session_factory, pg_engine
from app.domain.context.models import OrganizationNode

pytestmark = pytest.mark.asyncio

async def test_r8_validation(pg_session: AsyncSession):
    workspace_engine = WorkspaceEngine(pg_session)
    val_engine = ValidationEngine(pg_session)
    workspace_id = uuid.uuid4()
    
    # Needs provisioning first
    await workspace_engine.provision_workspace(
        workspace_id=workspace_id,
        owner_email=f"test_{workspace_id}@example.com",
        owner_name="Test User",
        password_hash="hashed"
    )
    
    # Should fail due to missing context
    results = await val_engine.run_checks(workspace_id)
    assert "BUSINESS_CONTEXT" in [r.check_name for r in results if r.status == "FAIL"]
    
    # Add context
    node = OrganizationNode(
        workspace_id=workspace_id,
        node_type="Company",
        name="Test Corp",
        source_system="MANUAL"
    )
    pg_session.add(node)
    await pg_session.commit()
    
    results = await val_engine.run_checks(workspace_id)
    # The warning for MISSING_COMMUNICATION might still exist, but context should pass
    context_res = next(r for r in results if r.check_name == "BUSINESS_CONTEXT")
    assert context_res.status == "PASS"
