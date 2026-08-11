import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import FastAPI, APIRouter, Depends
from pydantic import BaseModel

app = FastAPI()
router = APIRouter()

class ActionCreate(BaseModel):
    action_type: str
    target: dict

# Mock simple API
@router.post("/workspaces/{workspace_id}/actions")
def create_action(workspace_id: str, payload: ActionCreate):
    return {"id": str(uuid4()), "status": "DETECTED", "type": payload.action_type}

app.include_router(router)
client = TestClient(app)

def test_create_action_api():
    ws_id = str(uuid4())
    response = client.post(
        f"/workspaces/{ws_id}/actions",
        json={"action_type": "CREATE_TASK", "target": {"task": "do something"}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DETECTED"
    assert data["type"] == "CREATE_TASK"
    assert "id" in data
