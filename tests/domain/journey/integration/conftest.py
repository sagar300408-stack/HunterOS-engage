import pytest
from datetime import datetime

@pytest.fixture
def sample_metadata():
    return {
        "workspace_id": "ws-12345",
        "generated_at": datetime.utcnow(),
        "version": "1.0.0",
        "provenance": ["system:init", "pipeline:start"]
    }

@pytest.fixture
def sample_completeness_report():
    return {
        "score": 0.95,
        "missing_fields": [],
        "is_sufficient": True
    }

@pytest.fixture
def sample_intelligence_context(sample_metadata, sample_completeness_report):
    return {
        "metadata": sample_metadata,
        "completeness": sample_completeness_report,
        "entities": [{"id": "e-1", "type": "Account"}],
        "timeline": [{"event": "created", "timestamp": "2023-01-01T00:00:00Z"}],
        "metrics": {"engagement_score": 85}
    }

@pytest.fixture
def mock_gateway():
    class MockGateway:
        def assemble(self, request):
            return {"status": "success", "data": "mocked_context"}
    return MockGateway()
