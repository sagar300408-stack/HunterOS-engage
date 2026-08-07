"""
Integration Tests for Intent Intelligence API v1 & REST Router (Phase 2.3.5)
"""

from fastapi.testclient import TestClient
import pytest

from app.domain.intents.integration.api_v1 import intent_intelligence_api_v1
from app.domain.intents.integration.models import CompositionProfileType
from app.domain.intents.integration.schemas import (
    IntegrateIntentsRequest,
    QueryIntentContextRequest,
)
from app.domain.intents.router import router


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_api_v1_direct_integration():
    req = IntegrateIntentsRequest(
        conversation_id="conv_api_v1",
        entity_id="cust_api_1",
        workspace_id="ws_api_1",
        profile=CompositionProfileType.FULL,
    )
    resp = intent_intelligence_api_v1.integrate_intents(req)
    assert resp.success is True
    assert resp.context.conversation_id == "conv_api_v1"

    full = intent_intelligence_api_v1.get_full_intent_context("conv_api_v1")
    assert full is not None
    assert full.conversation_id == "conv_api_v1"

    profiles = intent_intelligence_api_v1.list_profiles()
    assert len(profiles) == 10

    q_req = QueryIntentContextRequest(
        workspace_id="ws_api_1",
    )
    q_results = intent_intelligence_api_v1.query_contexts(q_req)
    assert len(q_results) >= 1


def test_fastapi_rest_endpoints(client):
    # 1. Integrate endpoint
    payload = {
        "conversation_id": "conv_rest_test",
        "entity_id": "cust_rest",
        "workspace_id": "ws_rest",
        "profile": "FULL",
    }
    r = client.post("/api/v1/intents/integration/integrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["context"]["conversation_id"] == "conv_rest_test"

    # 2. Get Context
    r2 = client.get("/api/v1/intents/integration/context/conv_rest_test")
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == "conv_rest_test"

    # 3. Get Profiles
    r3 = client.get("/api/v1/intents/integration/profiles")
    assert r3.status_code == 200
    assert len(r3.json()) == 10

    # 4. Get Dashboard Export
    r4 = client.get("/api/v1/intents/integration/export/dashboard/conv_rest_test")
    assert r4.status_code == 200
    assert r4.json()["conversation_id"] == "conv_rest_test"

    # 5. Get Executive Export
    r5 = client.get("/api/v1/intents/integration/export/executive/conv_rest_test")
    assert r5.status_code == 200
    assert r5.json()["conversation_id"] == "conv_rest_test"
