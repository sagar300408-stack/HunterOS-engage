"""
Unit tests for Intent Evolution FastAPI Router endpoints.
"""

from datetime import datetime, timezone
import uuid
from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_router_strategies_endpoint():
    resp = client.get("/api/v1/intents/evolution/strategies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 8
    strategy_ids = [s["strategy_id"] for s in data]
    assert "StandardLifecycleStrategy" in strategy_ids
    assert "StandardConfidenceStrategy" in strategy_ids


def test_router_evolve_and_query_endpoints():
    entity_id = f"cust-api-{uuid.uuid4().hex[:6]}"
    conv_id = "conv-api-100"

    # 1. POST evolve
    payload = {
        "entity_id": entity_id,
        "conversation_id": conv_id,
        "entity_type": "CUSTOMER",
    }
    resp = client.post("/api/v1/intents/evolution/evolve", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["entity_id"] == entity_id
    assert res_data["diagnostics"]["is_valid"] is True

    # 2. GET entity timelines
    resp_timelines = client.get(f"/api/v1/intents/evolution/entity/{entity_id}/timelines")
    assert resp_timelines.status_code == 200

    # 3. GET analytics
    resp_analytics = client.get(f"/api/v1/intents/evolution/analytics/{entity_id}")
    assert resp_analytics.status_code == 200
    analytics_data = resp_analytics.json()
    assert analytics_data["entity_id"] == entity_id

    # 4. GET view
    resp_view = client.get(f"/api/v1/intents/evolution/views/{entity_id}/executive")
    assert resp_view.status_code == 200
    view_data = resp_view.json()
    assert view_data["view"] == "executive"
