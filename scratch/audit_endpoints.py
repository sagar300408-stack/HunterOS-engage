import sys
import json
import logging
import asyncio
import os
import uuid
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/hunteros"
os.environ["OPENAI_API_KEY"] = "test"
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test"
os.environ["APP_ENV"] = "testing"
os.environ["DASHBOARD_SECRET_KEY"] = "testsecretkey32charsminimumforsigning"

from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
import app.main
from app.integrations.postgres.database import get_db, get_db_session
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole

def mock_get_db():
    session = AsyncMock(spec=AsyncSession)
    yield session

test_user = User(
    id=uuid.uuid4(),
    workspace_id=uuid.uuid4(),
    email="test@test.com",
    role=UserRole.platform_admin,
    is_active=True
)

async def mock_get_current_user():
    return test_user

try:
    application = app.main.create_app()
    application.dependency_overrides[get_db] = mock_get_db
    application.dependency_overrides[get_db_session] = mock_get_db
    application.dependency_overrides[get_current_user] = mock_get_current_user
    
    # We also need to patch require_permission since it uses get_current_user but it might be constructed before our override
    # Actually FastAPI resolves nested dependencies so mock_get_current_user should apply to require_permission too.
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

client = TestClient(application)
results = []
test_id = str(uuid.uuid4())

print("Starting endpoint execution audit...")
for route in application.routes:
    if not isinstance(route, APIRoute):
        continue
    
    path = route.path
    methods = route.methods
    
    # Replace path parameters
    for param in ["workspace_id", "conversation_id", "customer_id", "event_id", "action_id", "approval_id", "plan_id", "pilot_id", "lead_id", "recommendation_id", "candidate_id", "followup_id", "installation_id", "integration_id"]:
        path = path.replace(f"{{{param}}}", test_id)
        
    path = path.replace("{template_name}", "standard")
    path = path.replace("{period}", "monthly")
    path = path.replace("{category}", "general")
    path = path.replace("{kpi_name}", "revenue")
    path = path.replace("{health_name}", "system")
    path = path.replace("{priority}", "high")
    path = path.replace("{role}", "admin")

    for method in methods:
        if method == "OPTIONS": continue
        
        status_code = None
        response_text = ""
        exception = None
        
        try:
            if method == "GET":
                res = client.get(path + "?q=test&limit=10&page=1&page_size=10")
            elif method == "POST":
                if "/webhook" in path:
                    res = client.post(path, json={"object": "whatsapp_business_account"})
                else:
                    res = client.post(path, json={})
            elif method == "PUT":
                res = client.put(path, json={})
            elif method == "DELETE":
                res = client.delete(path)
            elif method == "PATCH":
                res = client.patch(path, json={})
            
            status_code = res.status_code
            response_text = res.text
        except Exception as e:
            exception = str(e)
            
        results.append({
            "path": route.path,
            "method": method,
            "status": status_code,
            "exception": exception,
            "name": route.name,
            "module": route.endpoint.__module__
        })

output_path = "scratch/audit_results.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"Audit completed. Results saved to {output_path}")
