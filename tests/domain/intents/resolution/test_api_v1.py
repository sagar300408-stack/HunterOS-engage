"""
Unit tests for Frozen IntentResolutionAPIv1 contract.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.classification.models import (
    ClassifiedIntent,
    IntentClassificationResult,
)
from app.domain.intents.models import (
    DetectedIntent,
    IntentDetectionResult,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.resolution.api_v1 import IntentResolutionAPIv1
from app.domain.intents.resolution.repository import ResolutionRepository
from app.domain.intents.resolution.schemas import ResolveIntentsRequest


def test_api_v1_resolve_and_query_endpoints():
    repo = ResolutionRepository()
    api = IntentResolutionAPIv1(repository=repo)

    conv_id = "conv_api_test_01"
    ws_id = uuid.uuid4()
    req = ResolveIntentsRequest(
        conversation_id=conv_id,
        customer_id="cust_api_1",
        workspace_id=ws_id,
    )

    det_id = uuid.uuid4()
    detection_result = IntentDetectionResult(
        conversation_id=conv_id,
        workspace_id=ws_id,
        intents=[
            DetectedIntent(
                intent_id=det_id,
                intent_type=IntentType.PRICING_INQUIRY,
                taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
                confidence=0.91,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_1"]),
            )
        ],
    )

    # 1. Resolve Intents via API v1
    response = api.resolve_intents(
        request=req,
        detection_result=detection_result,
    )

    assert response is not None
    assert response.conversation_id == conv_id
    assert response.entity_id == "cust_api_1"
    assert response.workspace_id == str(ws_id)
    assert response.snapshot.node_count == 1
    assert response.analytics is not None

    res_id = uuid.UUID(response.resolution_id)

    # 2. Get Resolution by ID
    fetched = api.get_resolution(res_id)
    assert fetched is not None
    assert fetched.resolution_id == response.resolution_id

    # 3. Get Latest Resolution
    latest = api.get_latest_resolution(entity_type="CUSTOMER", entity_id="cust_api_1", workspace_id=ws_id)
    assert latest is not None
    assert latest.resolution_id == response.resolution_id

    # 4. Get Resolution Graph DTO strictly (User Directive 8)
    graph_dto = api.get_resolution_graph_dto(res_id)
    assert graph_dto is not None
    assert len(graph_dto.nodes) == 1
    assert str(det_id) in graph_dto.nodes

    # 5. Get Analytics
    analytics = api.get_analytics(res_id)
    assert analytics is not None
    assert analytics.average_group_size == 1.0

    # 6. Get CQRS Views
    exec_view = api.get_view(res_id, "EXECUTIVE")
    assert exec_view is not None
    assert exec_view["view_type"] == "EXECUTIVE"

    sales_view = api.get_view(res_id, "SALES")
    assert sales_view is not None
    assert sales_view["view_type"] == "SALES"

    ops_view = api.get_view(res_id, "OPERATIONS")
    assert ops_view is not None
    assert ops_view["view_type"] == "OPERATIONS"

    audit_view = api.get_view(res_id, "AUDIT")
    assert audit_view is not None
    assert audit_view["view_type"] == "AUDIT"
