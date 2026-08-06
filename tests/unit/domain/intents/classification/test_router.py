"""
Tests for FastAPI Classification REST endpoints.
"""

import uuid
from fastapi.testclient import TestClient
import pytest

from app.domain.intents.api import intent_api_v1
from app.domain.intents.classification.api import canonical_intent_api_v1
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionMethod,
    IntentDetectionResult,
    IntentDiagnostics,
    IntentEvidence,
    IntentMetadata,
    IntentProvenance,
    IntentTaxonomyCategory,
    IntentType,
)
from app.main import create_app

client = TestClient(create_app())


def test_classification_router_endpoints():
    conv_id = f"conv_router_test_{uuid.uuid4().hex[:8]}"
    ws_id = str(uuid.uuid4())

    # Pre-seed a detected intent in intent_api_v1 repo
    det_res = IntentDetectionResult(
        conversation_id=conv_id,
        workspace_id=uuid.UUID(ws_id),
        intents=[
            DetectedIntent(
                conversation_id=conv_id,
                workspace_id=uuid.UUID(ws_id),
                intent_type=IntentType.PRICING_INQUIRY,
                taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
                business_importance=BusinessImportance.COMMERCIAL,
                title="Commercial inquiry for software licenses",
                description="Needs enterprise pricing quotation.",
                confidence=0.91,
                detection_method=IntentDetectionMethod.RULE_BASED,
                supporting_evidence=IntentEvidence(text_snippets=["enterprise license pricing"]),
            )
        ],
        metadata=IntentMetadata(conversation_id=conv_id, total_intents=1),
        diagnostics=IntentDiagnostics(is_valid=True),
    )
    intent_api_v1._engine.repository.save(det_res)

    # 1. POST /api/v1/intents/classification/classify
    res = client.post(
        "/api/v1/intents/classification/classify",
        json={
            "conversation_id": conv_id,
            "workspace_id": ws_id,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["conversation_id"] == conv_id
    assert len(data["classified_intents"]) == 1
    assert data["metadata"]["total_classified_intents"] == 1
    classification_id = data["classification_id"]

    # 2. GET /api/v1/intents/classification/{classification_id}
    res_get = client.get(f"/api/v1/intents/classification/{classification_id}")
    assert res_get.status_code == 200
    assert res_get.json()["classification_id"] == classification_id

    # 3. GET /api/v1/intents/classification/conversation/{conversation_id}
    res_conv = client.get(f"/api/v1/intents/classification/conversation/{conv_id}")
    assert res_conv.status_code == 200

    # 4. GET /api/v1/intents/classification/conversation/{conversation_id}/intents
    res_intents = client.get(f"/api/v1/intents/classification/conversation/{conv_id}/intents")
    assert res_intents.status_code == 200
    assert len(res_intents.json()) == 1

    # 5. GET /api/v1/intents/classification/conversation/{conversation_id}/views/executive
    res_view = client.get(f"/api/v1/intents/classification/conversation/{conv_id}/views/executive")
    assert res_view.status_code == 200
    assert res_view.json()["view_type"] == "EXECUTIVE"

    # 6. GET /api/v1/intents/classification/taxonomy/graph
    res_graph = client.get("/api/v1/intents/classification/taxonomy/graph")
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()

    # 7. GET /api/v1/intents/classification/processes/list
    res_procs = client.get("/api/v1/intents/classification/processes/list")
    assert res_procs.status_code == 200
    assert len(res_procs.json()) >= 4

    # 8. GET /api/v1/intents/classification/plugins/list
    res_plugins = client.get("/api/v1/intents/classification/plugins/list")
    assert res_plugins.status_code == 200
    assert len(res_plugins.json()) >= 4

    # 9. GET /api/v1/intents/classification/analytics/summary
    res_analytics = client.get("/api/v1/intents/classification/analytics/summary")
    assert res_analytics.status_code == 200
    assert res_analytics.json()["total_classifications"] >= 1
