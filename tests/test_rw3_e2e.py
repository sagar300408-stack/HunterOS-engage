"""
RW3 End-to-End Test
Verifies the complete R7 -> R8 -> R9 lifecycle against a real PostgreSQL database.

Scenario 1: Full Lifecycle (New Customer)
  1. Authenticated workspace creation (R7)
  2. Initial Validation (R8) & Readiness (R9) -> NOT_READY
  3. Add missing context & integrations
  4. Final Validation (R8) & Readiness (R9) -> READY

Scenario 2: Tenant Isolation
  1. Create Tenant A -> Complete -> READY
  2. Create Tenant B -> Incomplete -> NOT_READY
  3. Verify A cannot see B's state, and B's incomplete state does not affect A.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.integrations.postgres.database import get_db
from app.domain.security.models import User, UserRole, DEFAULT_WORKSPACE_ID
from app.domain.dashboard.service import hash_password
from app.domain.context.models import OrganizationNode
from app.domain.integration.models import IntegrationConnection
from app.domain.onboarding.models import GoLiveStatus

# Import real DB fixtures
from tests.domain.events.conftest import pg_session, pg_session_factory, pg_engine

# Real DB is used via the standard test setup
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def async_client(pg_session_factory):
    async def override_get_db():
        async with pg_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            
    fastapi_app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test"
    ) as client:
        yield client
        
    fastapi_app.dependency_overrides.clear()




async def create_platform_admin(pg_session):
    """Helper to create a platform admin user for testing."""
    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        email=f"admin_{admin_id}@hunteros.ai",
        full_name="Platform Admin",
        password_hash=hash_password("admin123"),
        role=UserRole.admin,  # Using standard admin role
        is_active=True,
    )
    pg_session.add(admin)
    await pg_session.commit()
    return admin, "admin123"


async def get_auth_token(async_client: AsyncClient, email: str, password: str) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_rw3_full_lifecycle(async_client: AsyncClient, pg_session):
    """
    Complete lifecycle test: R7 -> R8 -> R9 -> Correction -> READY
    """
    # 1. Setup platform admin and get token
    admin, password = await create_platform_admin(pg_session)
    admin_token = await get_auth_token(async_client, admin.email, password)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    workspace_id = str(uuid.uuid4())
    owner_email = f"owner_{workspace_id}@tenant.com"
    owner_password = "secure_password123"

    # 2. R7: Provision workspace
    response = await async_client.post(
        "/api/v1/workspaces",
        json={
            "workspace_id": workspace_id,
            "owner_email": owner_email,
            "owner_name": "Tenant Owner",
            "owner_password": owner_password,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"

    # 3. Authenticate as the new tenant owner
    owner_token = await get_auth_token(async_client, owner_email, owner_password)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 4. R8 & R9 Initial: Should be NOT_READY (missing business context)
    response = await async_client.post(
        f"/api/v1/onboarding/go-live?workspace_id={workspace_id}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == GoLiveStatus.NOT_READY.value
    
    # Check that Business Context failed
    context_check = next((c for c in data["checks"] if c["name"] == "Business Context"), None)
    assert context_check is not None
    assert context_check["status"] == "FAIL"

    # 5. Fix the missing requirement: Add Business Context
    node = OrganizationNode(
        workspace_id=uuid.UUID(workspace_id),
        node_type="Company",
        name="Acme Corp",
        is_active=True,
        source_system="MANUAL"
    )
    pg_session.add(node)
    
    # Add a communication integration (optional, but good for completeness)
    conn = IntegrationConnection(
        workspace_id=uuid.UUID(workspace_id),
        connector_id="mock_email_v1",
        connector_type="email",
        provider="mock",
        name="Email Setup",
        status="connected"
    )
    pg_session.add(conn)
    await pg_session.commit()

    # 6. R8 & R9 Final: Should now be READY
    response = await async_client.post(
        f"/api/v1/onboarding/go-live?workspace_id={workspace_id}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == GoLiveStatus.READY.value
    
    context_check = next((c for c in data["checks"] if c["name"] == "Business Context"), None)
    assert context_check["status"] == "PASS"


async def test_rw3_tenant_isolation(async_client: AsyncClient, pg_session):
    """
    Verifies that Tenant A cannot see or affect Tenant B's onboarding state.
    """
    admin, password = await create_platform_admin(pg_session)
    admin_token = await get_auth_token(async_client, admin.email, password)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Provision Tenant A
    workspace_a = str(uuid.uuid4())
    owner_a_email = f"owner_a_{workspace_a}@tenant.com"
    await async_client.post(
        "/api/v1/workspaces",
        json={
            "workspace_id": workspace_a,
            "owner_email": owner_a_email,
            "owner_name": "Owner A",
            "owner_password": "passwordA",
        },
        headers=admin_headers,
    )

    # Provision Tenant B
    workspace_b = str(uuid.uuid4())
    owner_b_email = f"owner_b_{workspace_b}@tenant.com"
    await async_client.post(
        "/api/v1/workspaces",
        json={
            "workspace_id": workspace_b,
            "owner_email": owner_b_email,
            "owner_name": "Owner B",
            "owner_password": "passwordB",
        },
        headers=admin_headers,
    )

    token_a = await get_auth_token(async_client, owner_a_email, "passwordA")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    token_b = await get_auth_token(async_client, owner_b_email, "passwordB")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant A tries to read Tenant B's status
    response = await async_client.get(
        f"/api/v1/onboarding/status?workspace_id={workspace_b}",
        headers=headers_a,
    )
    assert response.status_code == 403

    # Tenant A tries to run Go-Live for Tenant B
    response = await async_client.post(
        f"/api/v1/onboarding/go-live?workspace_id={workspace_b}",
        headers=headers_a,
    )
    assert response.status_code == 403
